import json 


with open("mensuel_20240401_20240430.json", 'r', encoding = 'utf8') as f:
    data = json.load(f)
project =  data['releases'][10]
for item in project['contracts'] : 
    print(item)
