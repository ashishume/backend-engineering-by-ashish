import copy

a = [1, 2, [3]]
b = a.copy()

c = copy.deepcopy(a)      # deep
a.append(5)              # shallow

print(a)
print(b)
print(c)