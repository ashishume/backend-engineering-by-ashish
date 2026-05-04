from itertools import count


def lengthOfLongestSubstring(str) -> int:
    left, right = 0, 0
    n = len(str)
    max_count = 0
    st = set()
    while left < n and right < n:
        if str[right] not in st:
            st.add(str[right])
            right += 1
            max_count = max(max_count, right - left)
        else:
            st.discard(str[left])
            left += 1

    return max_count


print(lengthOfLongestSubstring("abcabcbb"))
