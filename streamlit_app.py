import streamlit as st
import pandas as pd
import polars as pl
import fastexcel

st.title("🎈 My new app")
st.write(
    "Let's start building! For help and inspiration, head over to [docs.streamlit.io](https://docs.streamlit.io/)."
)

# Read in file
df = pl.read_excel("data/Population estimates and components by SA2.xlsx", 
                   sheet_name="Table 2",
                   read_options={
                    "skip_rows": 6,
                    }
                   )
# Column names change
df.columns = ["GCCSA code",	"GCCSA name", "SA4 code", "SA4 name", "SA3 code",
              "SA3 name", "SA2 code", "SA2 name","2023 Pop", "2024 Pop",
              "2023-24 Change", "2023-24 Change %", "Natural Increase", "Net internal migration",
              "Net oveseas migration","Area","Population Density"]


# Clean and load dataset
df_stg = (
    df
        .select("SA3 name","SA3 code","SA2 name", "SA2 code", "2024 Pop", "2023-24 Change", "Area")
        .head(df.height - 2)
        .with_columns(
            pl.when(pl.col("SA2 name").str.contains("-"))
            .then(
                pl.col("SA2 name")
                    .str.extract(r"^(.*?)-", 1)
                    .str.strip_chars(" ")  # remove leading/trailing spaces
                )
            .otherwise(pl.col("SA2 name"))
            .alias("Suburb")
        )
        .with_columns(
            pl.when(pl.col("SA3 name").str.contains("-"))
            .then(
                pl.col("SA3 name")
                    .str.extract(r"^(.*?)-", 1)
                    .str.strip_chars(" ")  # remove leading/trailing spaces
                )
            .otherwise(pl.col("SA3 name"))
            .alias("Council")
        )
        .select("Council","Suburb","2024 Pop","2023-24 Change","Area")

        .group_by(["Council","Suburb"])
        .agg(
            pl.sum("2024 Pop").alias("2024 Pop"),
            pl.sum("2023-24 Change").alias("2023-24 Change"),
            pl.sum("Area").alias("Suburb Area km^2")
        )
        # Add average pop
        .with_columns(
            pl.col("2024 Pop")
            .mean()
            .over("Council")
            .round(0).cast(pl.Int64) 
            .alias("avg_suburb_pop_in_Council")
        )
        # Add average area
        .with_columns(
            pl.col("Suburb Area km^2")
            .mean()
            .over("Council")
            .round(0).cast(pl.Int64) 
            .alias("avg_suburb_area_in_Council")
        )
        .sort("Council", descending=False)
        .filter(pl.col("Council") == "Darebin")

        .select("Council","Suburb","2024 Pop","avg_suburb_pop_in_Council",
                "Suburb Area km^2","avg_suburb_area_in_Council",
                "2023-24 Change")
        
)

# Create dropdown menu
selected_category = st.selectbox(
    'Select Suburb:',
    options=['All'] + list(df_stg['Suburb'].unique())
)

# Filter data based on selection
if selected_category == 'All':
    filtered_df = df_stg
else:
    filtered_df = (
        df_stg.filter(
            pl.col("Suburb") == selected_category
        )
    )

# Display filtered data
st.dataframe(
    filtered_df,
    width=800,
    height=400
    )