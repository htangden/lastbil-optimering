#!/usr/bin/env python
from pulp import LpVariable, LpProblem, LpMinimize, LpInteger, lpSum, value, PULP_CBC_CMD
from geopy.distance import geodesic
from itertools import combinations
from typing import Tuple
import math
import sys

TRAIN_TO_TRUCK = 10


class Building:

    def __init__(self, pos : Tuple[float, float], name : str):
        self.pos = pos
        self.name = name

    def distanceTo(self, other: "Building") -> float:
        return geodesic(self.pos, other.pos).kilometers
    
    def __str__(self):
        return self.name
    
    def __repr__(self):
        return self.name
    

class Factory(Building):
    
    def __init__(self, pos : Tuple[float, float], name : str, production_quantity : float):
        super().__init__(pos, name)
        self.production_quantity = production_quantity

class Supplier(Building):

    def __init__(self, pos : Tuple[float, float], name : str, needed : float):
        super().__init__(pos, name)
        self.needed = needed

 

def weighted_midpoint(suppliers : list[Supplier], factories : list[Factory]) -> Tuple[float, float]:
    coords = [building.pos for building in suppliers + factories]
    a = [supplier.needed for supplier in suppliers] + [factory.production_quantity/TRAIN_TO_TRUCK for factory in factories]

    x_coords, y_coords = zip(*coords)

    ak2 = sum([ak**2 for ak in a])
    ak2_xk = sum([a[i]**2*x_coords[i] for i in range(len(a))])
    ak2_yk = sum([a[i]**2*y_coords[i] for i in range(len(a))])

    x = ak2_xk/ak2
    y = ak2_yk/ak2
    return (x, y)




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


def run_with_midpoint(suppliers, factories, midpoint_pos):

    model = LpProblem(f"lastbilsproblem {name}", LpMinimize)

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
        model += lpSum(truck_from_factory for truck_from_factory in num_trucks[i]) <= building.production_quantity, f"Lastbilsbegränsning {building}"

    for i, supplier in enumerate(suppliers_with_midpoint):
        trucks_to_supplier = [row[i] for row in num_trucks]
        sum_to_supplier = lpSum(truck_to_supplier for truck_to_supplier in trucks_to_supplier)
        sum_from_supplier = lpSum(truck_from_supplier for truck_from_supplier in num_trucks[len(factories) + i])
        model += (sum_to_supplier - sum_from_supplier) == supplier.needed, f"Rätt mängd till {supplier}"


    model.writeLP("lastbil.lp")
    model.solve(PULP_CBC_CMD(msg=False))
    return model


models = []

for r in range(1, len(suppliers)):
    for supplier_combo in combinations(suppliers, r):
        midpoint = weighted_midpoint(list(supplier_combo), factories)
        models.append(run_with_midpoint(suppliers, factories, midpoint))
        print(supplier_combo, value(models[-1].objective))

best_model = min(models, key=lambda x: value(x.objective))


with open("solution.txt", "w") as f:
    f.write("OPTIMALA VÄRDEN:\n")
    for v in best_model.variables():
        if (v.varValue != 0):
            f.write(f"{v.name} = {v.varValue}\n")
    f.write(f"\nPOSITION MELLANLAGER: ({suppliers[-1].pos[0]:.2f}, {suppliers[-1].pos[1]:.2f}) ")
    f.write(f"\nSTRÄCKA KÖRD: {value(best_model.objective):.2f}")



