def longestCommonPrefix(strs):
    i, j = 0, 0
    n = len(strs[0])
    prefix = strs[0]
    for ch in strs:
        n = min(n, len(ch))

    print(n)
    for ch in strs[1:]:
        while ch.find(prefix) != 0:
            prefix = prefix[:-1]
            if prefix == "":
                return ""

    return prefix


print(longestCommonPrefix(["dog", "racecar", "car"]))
# print(longestCommonPrefix(["interview", "inter", "internal"]))
