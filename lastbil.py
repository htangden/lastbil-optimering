#!/usr/bin/env python
from pulp import LpVariable, LpProblem, LpMinimize, LpInteger, lpSum, value, PULP_CBC_CMD
from scipy.optimize import minimize
from geopy.distance import geodesic
from numpy import sin, cos, sqrt, radians, atan2
from itertools import combinations
import matplotlib.pyplot as plt
import cartopy.crs as ccrs
import cartopy.feature as cfeature
from tqdm import tqdm
from typing import Tuple
import math
import sys

TRAIN_TO_TRUCK = 10
EARTH_RADIUS = 6378


class Building:

    def __init__(self, pos : Tuple[float, float], name : str):
        self.pos = pos
        self.name = name

    def distanceTo(self, other: "Building") -> float:
        return geodesic(self.pos, other.pos).kilometers
    
    def __str__(self):
        return self.name

    

class Factory(Building):
    
    def __init__(self, pos : Tuple[float, float], name : str, production_quantity : float):
        super().__init__(pos, name)
        self.production_quantity = production_quantity

class Supplier(Building):

    def __init__(self, pos : Tuple[float, float], name : str, needed : float):
        super().__init__(pos, name)
        self.needed = needed

 


#Create factories, suppliers from file
factories, suppliers = [], []
with open(sys.argv[1]) as file:
    section = None
    for line in file:
        line = line.strip()
        if not line:
            continue
        elif line == "FABRIKER":
            section = "FABRIKER"
        elif line == "GROSSISTER":
            section = "GROSSISTER"
        else:
            name, x, y, capacity = line.split()
            (factories if section == "FABRIKER" else suppliers).append(
                (Factory if section == "FABRIKER" else Supplier)((float(x), float(y)), name, int(capacity))
            )



def weighted_midpoint(suppliers : list[Supplier], factories : list[Factory]) -> Tuple[float, float]:
    coords = [building.pos for building in suppliers + factories]
    a = [supplier.needed for supplier in suppliers] + [factory.production_quantity/TRAIN_TO_TRUCK for factory in factories]

    x_coords, y_coords = zip(*coords)

    ak2 = sum([ak**2 for ak in a])
    ak2_xk = sum([a[i]**2*x_coords[i] for i in range(len(a))])
    ak2_yk = sum([a[i]**2*y_coords[i] for i in range(len(a))])

    #initial guess
    x = ak2_xk/ak2
    y = ak2_yk/ak2


    def distance(point):
        return sum([a[i] * geodesic(point, coords[i]).kilometers for i in range(len(coords))])
        

    def haversine_distance(point):
        lon, lat = point  
        lon, lat = radians(lon), radians(lat)  

        total_distance = 0
        for i, (xk, yk) in enumerate(coords):
            xk, yk = radians(xk), radians(yk)  
            dlon = lon - xk
            dlat = lat - yk
            alfa = sin(dlat / 2) ** 2 + cos(lat) * cos(yk) * sin(dlon / 2) ** 2
            c = 2 * atan2(sqrt(alfa), sqrt(1 - alfa))
            total_distance += EARTH_RADIUS * c * a[i] 

        return total_distance
    
    long, lat = minimize(distance, x0=[x, y]).x
    return long, lat



def run_with_midpoint(suppliers, factories, midpoint_pos : Tuple[float, float]):

    model = LpProblem(f"lastbilsproblem_{name}", LpMinimize)

    suppliers_with_midpoint = suppliers + [Supplier(midpoint_pos, "Mellanlager", 0)]

    road_len = []
    num_trucks = []

    for i, building in enumerate(factories + suppliers_with_midpoint):
        num_trucks.append([])
        road_len.append([])
        for j, supplier in enumerate(suppliers_with_midpoint):
            num_trucks[i].append(LpVariable(f"LASTBILAR:{building}_{supplier}", 0, None, LpInteger))
            road_len[i].append(building.distanceTo(supplier))


    for row in road_len:
        row[-1] /= TRAIN_TO_TRUCK

    model += lpSum(road_len[i][j] * num_trucks[i][j] for i in range(len(factories + suppliers_with_midpoint)) for j in range(len(suppliers_with_midpoint)))


    for i, building in enumerate(factories):
        model += lpSum(truck_from_factory for truck_from_factory in num_trucks[i]) <= building.production_quantity, f"Lastbilsbegränsning_{building}"

    for i, supplier in enumerate(suppliers_with_midpoint):
        trucks_to_supplier = [row[i] for row in num_trucks]
        sum_to_supplier = lpSum(truck_to_supplier for truck_to_supplier in trucks_to_supplier)
        sum_from_supplier = lpSum(truck_from_supplier for truck_from_supplier in num_trucks[len(factories) + i])
        model += (sum_to_supplier - sum_from_supplier) == supplier.needed, f"Rätt mängd till {supplier}"


    model.writeLP("output/lastbil.lp")
    model.solve(PULP_CBC_CMD(msg=False))
    return model


models = []
positions = []

for amount_of_factories in range(1, len(factories) + 1):
    for factory_combo in combinations(factories, amount_of_factories):
        for amount_of_suppliers in range(1, len(suppliers) + 1):
            for supplier_combo in combinations(suppliers, amount_of_suppliers):
                midpoint = weighted_midpoint(list(supplier_combo), list(factory_combo))
                model = run_with_midpoint(suppliers, factories, midpoint)
                models.append(model)
                positions.append(midpoint)
                # print([str(obj) for obj in factory_combo+supplier_combo], value(models[-1].objective))


best_model = min(models, key=lambda x: value(x.objective))
best_position = positions[models.index(best_model)]

# best_model = run_with_midpoint(suppliers, factories, (55, 15))
# best_position = (55, 15)

with open("output/solution.txt", "w") as f:
    f.write("OPTIMALA VÄRDEN:\n")
    for v in best_model.variables():
        if (v.varValue != 0):
            f.write(f"{v.name} = {v.varValue}\n")
    f.write(f"\nPOSITION MELLANLAGER: ({best_position[0]:.2f}, {best_position[1]:.2f}) ")
    f.write(f"\nSTRÄCKA KÖRD: {value(best_model.objective):.2f}")


buildings = factories + suppliers + [Building(best_position, "Mellanlager")]
lons = [b.pos[1] for b in buildings]
lats = [b.pos[0] for b in buildings]

lats_sup = [s.pos[0] for s in suppliers]
lats_fac = [f.pos[0] for f in factories]
lons_sup = [s.pos[1] for s in suppliers]
lons_fac = [f.pos[1] for f in factories]
names = [b.name for b in buildings]

connections = []
for v in best_model.variables():
    if (v.varValue != 0):
        name = v.name[10:].split("_")
        Building1 = [b for b in buildings if b.name == name[0]][0]
        Building2 = [b for b in buildings if b.name == name[1]][0]
        connections.append([Building1, Building2, v.varValue])

fig, ax = plt.subplots(figsize=(10, 6), subplot_kw={'projection': ccrs.PlateCarree()})

try:
    add_atlas = (sys.argv[2] != "False")
except IndexError:
    add_atlas = True

if add_atlas:
    ax.add_feature(cfeature.COASTLINE)
    ax.add_feature(cfeature.BORDERS, linestyle=":")
    ax.add_feature(cfeature.LAND, edgecolor="black", facecolor="lightgray")
    ax.add_feature(cfeature.OCEAN, facecolor="lightblue")



ax.scatter(lons_sup, lats_sup, color="green", s=75, label="Grossister")
ax.scatter(lons_fac, lats_fac,color="red", s=75, label="Fabriker")
ax.scatter(best_position[1], best_position[0], color="purple", s=75, label="Mellanlager")

for i, name in enumerate(names):
    ax.text(lons[i] + 0.5, lats[i], name, fontsize=12, verticalalignment="bottom", horizontalalignment="right", color="black")

for b1, b2, num in connections:
    x_vals = [b1.pos[1], b2.pos[1]]  
    y_vals = [b1.pos[0], b2.pos[0]]  
    ax.plot(x_vals, y_vals, color="blue", linewidth=2, linestyle="--")


    mid_x, mid_y = (x_vals[0] + x_vals[1]) / 2, (y_vals[0] + y_vals[1]) / 2
    ax.text(mid_x, mid_y, str(num), fontsize=12, color="black", weight="bold", ha="center", va="center", bbox=dict(facecolor="white", alpha=0.7))


ax.set_title("Lastbilsplanering", fontsize=14)
ax.set_aspect('auto')
plt.legend()
plt.savefig("output/solution.png")
plt.show()

