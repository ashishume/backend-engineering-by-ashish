def maxSubArray(nums):
    n = len(nums)
    sum = (n * (n + 1)) / 2
    curr_sum = 0
    for num in nums:
        curr_sum += num
    return int(sum - curr_sum)


print(maxSubArray([0, 1, 2, 4, 5, 6]))
