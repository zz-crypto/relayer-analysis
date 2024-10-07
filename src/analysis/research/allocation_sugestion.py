import pandas as pd

def optimize_allocation_dp(csv_file, total_allocation):

    df = pd.read_csv(csv_file)

    step = 5000
    total_steps = int(total_allocation / step)

    combos = {}
    for _, row in df.iterrows():
        key = (
            row["origin_chain"],
            row["destination_chain"],
            row["input_symbol"],
            row["output_symbol"],
        )
        if key not in combos:
            combos[key] = []
        combos[key].append(row)

    dp = [0] * (total_steps + 1)
    allocations = [[] for _ in range(total_steps + 1)]

    for combo, rows in combos.items():
        new_dp = dp.copy()
        new_allocations = [alloc.copy() for alloc in allocations]

        for i in range(total_steps + 1):
            current_allocation = i * step
            max_profit = 0
            best_allocation = 0
            best_row = None

            for j in range(i + 1):
                allocation = j * step
                for row in rows:
                    if allocation >= row["simulated_allocation"]:

                        profit = min(row["profit"], row["profit_ratio"] * allocation)
                        remaining = i - j
                        total_profit = profit + dp[remaining]

                        if total_profit > max_profit:
                            max_profit = total_profit
                            best_allocation = allocation
                            best_row = row

            if max_profit > new_dp[i]:
                new_dp[i] = max_profit
                remaining = i - int(best_allocation / step)
                new_allocations[i] = allocations[remaining] + [
                    (combo, best_allocation, max_profit - dp[remaining])
                ]

        dp = new_dp
        allocations = new_allocations

    best_allocation = allocations[-1]
    total_profit = dp[-1]

    result = []
    for (
        (origin_chain, destination_chain, input_symbol, output_symbol),
        allocation,
        profit,
    ) in best_allocation:
        result.append(
            {
                "origin_chain": origin_chain,
                "destination_chain": destination_chain,
                "input_symbol": input_symbol,
                "output_symbol": output_symbol,
                "allocation": allocation,
                "expected_profit": profit,
            }
        )

    return result, total_profit


total_allocation = 1000000
allocations, total_expected_profit = optimize_allocation_dp(
    "simulation_results.csv", total_allocation
)


print(f"Optimal allocations for ${total_allocation:.2f}:")
for alloc in allocations:
    print(
        f"{alloc['origin_chain']} to {alloc['destination_chain']} - {alloc['input_symbol']} to {alloc['output_symbol']}: ${alloc['allocation']:.2f} (Expected profit: ${alloc['expected_profit']:.2f})"
    )

print(f"\nTotal expected profit: ${total_expected_profit:.2f}")
print(f"Total allocated: ${sum(alloc['allocation'] for alloc in allocations):.2f}")
