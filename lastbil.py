#!/usr/bin/env python
from pulp import LpVariable, LpProblem, LpMinimize, LpInteger, lpSum, value
from geopy.distance import geodesic
from typing import Tuple
import math
import sys


class Building:

    def __init__(self, pos : Tuple[float, float], name : str):
        self.pos = pos
        self.name = name

    def distanceTo(self, other: "Building") -> float:
        return geodesic(self.pos, other.pos).kilometers
    
    def __str__(self):
        return self.name
    
    def dms_to_decimal(self, degrees, minutes, seconds, direction):
        decimal = degrees + minutes / 60 + seconds / 3600
        if direction in ['S', 'W']:
            decimal *= -1
        return decimal

class Factory(Building):
    
    def __init__(self, pos : Tuple[float, float], name : str, production_quantity : float):
        super().__init__(pos, name)
        self.production_quantity = production_quantity

class Supplier(Building):

    def __init__(self, pos : Tuple[float, float], name : str, needed : float):
        super().__init__(pos, name)
        self.needed = needed

 


model = LpProblem("lastbilsproblem ", LpMinimize)



path_to_data = sys.argv[1]

factories, suppliers = [], []

with open(path_to_data) as file:
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
    

road_len = []
num_trucks = []

for i, building in enumerate(factories + suppliers):
    num_trucks.append([])
    road_len.append([])
    for j, supplier in enumerate(suppliers):
        num_trucks[i].append(LpVariable(f"LASTBILAR:{building}_{supplier}", 0, None, LpInteger))
        road_len[i].append(building.distanceTo(supplier))

print(road_len)

model += lpSum(road_len[i][j] * num_trucks[i][j] for i in range(len(factories + suppliers)) for j in range(len(suppliers)))


for i, building in enumerate(factories):
    model += lpSum(truck_from_factory for truck_from_factory in num_trucks[i]) <= building.production_quantity, f"Lastbilsbegränsning {building}"

for i, supplier in enumerate(suppliers):
    trucks_to_supplier = [row[i] for row in num_trucks]
    sum_to_supplier = lpSum(truck_to_supplier for truck_to_supplier in trucks_to_supplier)
    sum_from_supplier = lpSum(truck_from_supplier for truck_from_supplier in num_trucks[len(factories) + i])
    model += (sum_to_supplier - sum_from_supplier) == supplier.needed, f"Rätt mängd till {supplier}"


model.writeLP("lastbil.lp")
model.solve()

with open("solution.txt", "w") as f:
    f.write("OPTIMALA VÄRDEN:\n")
    for v in model.variables():
        if (v.varValue != 0):
            f.write(f"{v.name} = {v.varValue}\n")
    f.write(f"\nSTRÄCKA KÖRD:\n{value(model.objective):.2f}")
