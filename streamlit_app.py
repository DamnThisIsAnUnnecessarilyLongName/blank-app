import streamlit as st
import pandas as pd
import polars as pl
import fastexcel


# Functions
def create_metric(label, value, font_size="28px"):
    return f"""
    <div style='text-align: center; padding: 20px; background-color: #f8f9fa; border-radius: 10px;'>
        <div style='font-size: 12px; color: #666;'>{label}</div>
        <div style='font-size: {font_size}; font-weight: bold;'>{value}</div>
    </div>
    """
def create_row_crime_metrics(source_df, title, subdivision_value):
    title_col, select_col, hier_col = st.columns(3)

    with title_col:
        st.metric(
            label = "",
            value = title
        )
    if selected_category == 'All':
        x = source_df.filter(pl.col("Offence Subdivision")==subdivision_value).select(pl.col('Incidents Recorded 2025').sum()).item()
        x1 = source_df.filter(pl.col("Offence Subdivision")==subdivision_value).select(pl.col('# change').sum()).item()

        # Assault Metric KPI
        with select_col:
            st.metric(
                label = "",
                value = f"{x:,}",
                delta = f"{x1:,}"
            )
    else:
        with select_col:
            x = source_df.filter(pl.col("Suburb/Town Name") == selected_category).filter(pl.col("Offence Subdivision")==subdivision_value).select(pl.col('Incidents Recorded 2025').sum()).item()
            x1 =source_df.filter(pl.col("Suburb/Town Name") == selected_category).filter(pl.col("Offence Subdivision")==subdivision_value).select(pl.col('# change').sum()).item()
            suburb = selected_category

            st.metric(
                label = "",
                value = f"{x:,}",
                delta = f"{x1:,}"
            )
        with hier_col:
            sel_council = source_df.filter(pl.col("Suburb/Town Name") == selected_category).filter(pl.col("Offence Subdivision")==subdivision_value).select(pl.col('Local Government Area')).item()
            x = int(source_df.filter(pl.col("Local Government Area") == sel_council).filter(pl.col("Offence Subdivision")==subdivision_value).select(pl.col('Incidents Recorded 2025').mean()).item())
            x1 = int(source_df.filter(pl.col("Local Government Area") == sel_council).filter(pl.col("Offence Subdivision")==subdivision_value).select(pl.col('# change').mean()).item())
            
            st.metric(
                label = "",
                value = f"{x:,}",
                delta = f"{x1:,}"
            )
#########################################################################
st.title("🎈 What is this suburb like?")
st.write(
    "Whether you are looking to move to a new suburb, or just curious to " \
    "know more about a suburb around Melbourne " \
    "this app provides concrete data that cuts through rumours/speculation " \
    "and provides data-backed insights on places around Melbourne"
)
st.write("This website is volunteer run and non-for-profit - "
"if you find it useful, please support by [donating here](%s) 😊" 
% "https://donate.stripe.com/bJe6oHe5W2aqf2CdMN7bW00")
st.write("Created by: [Marcus F](%s)" % "https://www.linkedin.com/in/marcus-f-a7505483/")

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

        .select("Council","Suburb","2024 Pop","avg_suburb_pop_in_Council",
                "Suburb Area km^2","avg_suburb_area_in_Council",
                "2023-24 Change")
        
)

df_stg.columns = ["Council","Suburb","Population","avg_suburb_pop_in_Council",
                "Area km^2","avg_suburb_area_in_Council",
                "Population Change"]
# ingest pop data
df_stg = df_stg.select("Council","Suburb","Population",
                       "Area km^2","Population Change")

# Create dropdown menu
selected_category = st.selectbox(
    'Select Suburb:',
    options=['All'] + list(df_stg['Suburb'].unique().sort())
)

# Summary - population
title_col, select_col, hier_col = st.columns(3)

with title_col:
    st.metric(
        label = "",
        value = "# Residents"
    )


# Filter data based on selection

if selected_category == 'All':
    x = df_stg.select(pl.col('Population').sum()).item()
    x1 = df_stg.select(pl.col('Population Change').sum()).item()
    filtered_df = df_stg

    # Population Metric KPI
    with select_col:
        st.metric(
            label = "VIC",
            value = f"{x:,}",
            delta = f"{x1:,}"
        )
else:
    filtered_df = (
        df_stg.filter(
            pl.col("Suburb") == selected_category
        )
    )

    with select_col:
        x = df_stg.filter(pl.col("Suburb") == selected_category).select(pl.col('Population').sum()).item()
        x1 =df_stg.filter(pl.col("Suburb") == selected_category).select(pl.col('Population Change').sum()).item()
        suburb = selected_category

        st.metric(
            label = suburb,
            value = f"{x:,}",
            delta = f"{x1:,}"
        )
    with hier_col:
        sel_council = df_stg.filter(pl.col("Suburb") == selected_category).select(pl.col('Council')).item()
        x = int(df_stg.filter(pl.col("Council") == sel_council).select(pl.col('Population').mean()).item())
        x1 = int(df_stg.filter(pl.col("Council") == sel_council).select(pl.col('Population Change').mean()).item())
        
        st.metric(
            label = sel_council + " Council Avg",
            value = f"{x:,}",
            delta = f"{x1:,}"
        )

## Summary - crimes
# ingest crimes data
df_crime = pl.read_csv("data/df_crime_stg.csv")

st.write("Crime Profile")

# Crime Metric KPIs
create_row_crime_metrics(df_crime, '# Assault', 'A20 Assault and related offences')
create_row_crime_metrics(df_crime, '# Theft', 'B40 Theft')

## crimes data table

df_crime = (
        df_crime.select(
            ["Suburb/Town Name", "Offence Division", 
            'Offence Subdivision',"Incidents Recorded 2025",
            "# change","Incidents Recorded 2024","% change"
            ]
            )
        )  

if selected_category == 'All':
    df_filtered_crime = df_crime

else:
    df_filtered_crime = (
        df_crime
        .filter(
            pl.col("Suburb/Town Name") == selected_category
        )
        .sort("Offence Subdivision")[:,1:7]
    )


st.dataframe(
    df_filtered_crime,
    width=1000,
    height=400
)

# Display filtered data
st.dataframe(
    filtered_df,
    width=800,
    height=400
    )

""
st.write("Source Data: Australian Bureau of Statistics (ABS)")

