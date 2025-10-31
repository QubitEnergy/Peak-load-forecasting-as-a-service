import pandas as pd

# Read the results CSV
df = pd.read_csv("rolling_variability_all_units.csv")

# Group by unit and compute an aggregate metric; here we'll take the maximum coefficient of variation for each unit.
agg = df.groupby("name")["rolling_coeff_var"].max()

# Sort units by their maximum coefficient of variation, descending (highest variability first)
top_units = agg.sort_values(ascending=False)

print("Top 10 units by maximum coefficient of variation:")
print(top_units.head(10))

# Read the results CSV
df = pd.read_csv("variability_results.csv")

# Group by unit and compute an aggregate metric; here we'll take the maximum coefficient of variation for each unit.
agg = df.groupby("name")["coeff_var"].max()

# Sort units by their maximum coefficient of variation, descending (highest variability first)
top_units = agg.sort_values(ascending=False)

print("Top 10 units by maximum coefficient of variation:")
print(top_units.head(10))
