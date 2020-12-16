lines = []

with open("maps/mst_campus.txt", "r") as fp:
    data = fp.read().split("\n")
    for string in data:
        string = string[::-1]
        lines.append(string)

with open("maps/reversed_mst_campus.txt", "w") as fp:
    fp.write("\n".join(lines))
