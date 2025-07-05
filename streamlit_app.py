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

#########################################################################
tab1, tab2, tab3 = st.tabs(["Overview", "Definitions", "Release Notes"])

with tab1:

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

    df_map = pl.read_csv("data/mapping_fnl.csv").with_columns(pl.col("Suburb/Town Name").str.replace("Melbourne", "Melbourne CBD"))

    df_stg2 = (
        df_stg
        .join(
            df_map,
            how='left',
            left_on='Suburb',
            right_on='Suburb/Town Name'
        )
        .select(["Council","Suburb","Population", "Area km^2","Population Change", 'Region'])
        )

    # Create dropdown menu
    selected_category = st.selectbox(
        'Select Suburb:',
        options=['All'] + list(df_stg2['Suburb'].unique().sort()),
        index=1
    )
    st.write("Data snapshot - 2025")

    # Summary - population
    title_col, select_col, hier_col = st.columns(3)

    with title_col:
        st.metric(
            label = "resident title",
            label_visibility='hidden',
            value = "😐 Residents"
        )
    # Filter data based on selection

    if selected_category == 'All':
        x = df_stg2.select(pl.col('Population').sum()).item()
        x1 = df_stg2.select(pl.col('Population Change').sum()).item()
        filtered_df = df_stg2

        # Population Metric KPI
        with select_col:
            st.metric(
                label = "VIC",
                value = f"{x:,}",
                delta = f"{x1:,}"
            )
    else:
        filtered_df = (
            df_stg2.filter(
                pl.col("Suburb") == selected_category
            )
        )

        with select_col:
            x = df_stg2.filter(pl.col("Suburb") == selected_category).select(['Population']).item(0,0)
            x1 =df_stg2.filter(pl.col("Suburb") == selected_category).select(['Population Change']).item(0,0)
            suburb = selected_category

            st.metric(
                label = suburb,
                value = f"{x:,}",
                delta = f"{x1:,}"
            )
        with hier_col:
            sel_region = df_stg2.filter(pl.col("Suburb") == selected_category).select(pl.col('Region')).item()
            x = int(df_stg2.filter(pl.col("Region") == sel_region).select(pl.col('Population').mean()).item())
            x1 = int(df_stg2.filter(pl.col("Region") == sel_region).select(pl.col('Population Change').mean()).item())
            
            st.metric(
                label = sel_region + " Avg",
                value = f"{x:,}",
                delta = f"{x1:,}"
            )

    ## Summary - Area
    title_col, select_col, hier_col = st.columns(3)

    with title_col:
        st.metric(
            label = "resident title",
            label_visibility='hidden',
            value = "📐 Area km^2"
        )
    # Filter data based on selection

    if selected_category == 'All':
        x = int(df_stg2.select(pl.col('Area km^2').mean()).item())
        filtered_df = df_stg2

        # Area Metric KPI
        with select_col:
            st.metric(
                label = "VIC",
                value = f"{x:,}"
            )
    else:
        filtered_df = (
            df_stg2.filter(
                pl.col("Suburb") == selected_category
            )
        )

        with select_col:
            x = df_stg2.filter(pl.col("Suburb") == selected_category).select(['Area km^2']).item(0,0)
            suburb = selected_category

            st.metric(
                label = suburb,
                value = f"{x:,}",
            )
        with hier_col:
            sel_region = df_stg2.filter(pl.col("Suburb") == selected_category).select(pl.col('Region')).item()
            x = round(df_stg2.filter(pl.col("Region") == sel_region).select(pl.col('Area km^2').mean()).item(),1)
            
            st.metric(
                label = sel_region + " Avg",
                value = f"{x:,}"
            )



    ## Summary - crimes
    # ingest crimes data
    df_crime = pl.read_csv("data/df_crime_suburb.csv")

    st.write("Crime Profile")

    # Crime Metric KPIs
    title_col, select_col, hier_col = st.columns(3)
    with title_col:
        st.metric(
            label = "crime_title",
            label_visibility='hidden',
            value = "🔪 Incidents"
        )
    # Filter data based on selection
    if selected_category == 'All':
        x = df_crime.select(pl.col('Incidents Recorded 2025').sum()).item()
        x1 = df_crime.select(pl.col('# change').sum()).item()
        filtered_df = df_crime

        # Crime Metric KPI
        with select_col:
            st.metric(
                label = "VIC",
                value = f"{x:,}",
                delta = f"{x1:,}"
            )
    else:
        filtered_df = (
            df_crime.filter(
                pl.col("Suburb/Town Name") == selected_category
            )
        )

        with select_col:
            x = df_crime.filter(pl.col("Suburb/Town Name") == selected_category).select(['Incidents Recorded 2025']).sum().item()
            x1 =df_crime.filter(pl.col("Suburb/Town Name") == selected_category).select(['# change']).sum().item()
            suburb = selected_category

            st.metric(
                label = suburb,
                value = f"{x:,}",
                delta = f"{x1:,}"
            )
        with hier_col:
            sel_region = df_crime.filter(pl.col("Suburb/Town Name") == selected_category).select(['Region']).head(1).item()
            y = int(df_crime.filter(pl.col("Region") == sel_region).group_by('Suburb/Town Name').agg(pl.sum("Incidents Recorded 2025")).select(['Incidents Recorded 2025']).mean().item())
            y1 = int(df_crime.filter(pl.col("Region") == sel_region).group_by('Suburb/Town Name').agg(pl.sum("# change")).select(['# change']).mean().item())
            
            st.metric(
                label = sel_region + " Avg",
                value = f"{y:,}",
                delta = f"{y1:,}"
            )



    ## crimes data table

    if selected_category == 'All':
        df_filtered_crime = df_crime

    else:
        sel_region = df_stg2.filter(pl.col("Suburb") == selected_category).select(pl.col('Region')).item()
        sel_suburb = selected_category

        df_crime_summary_stg=(
            df_crime
                .filter(pl.col('Suburb/Town Name')==sel_suburb)
                .with_columns(pl.col("Offence Division").str.slice(2))
                .group_by(['Offence Division'])
                .agg([
                    pl.sum("Incidents Recorded 2025").alias(sel_suburb + ' Incidents')
                    ,pl.sum("# change").alias(sel_suburb + ' Incident Change')
                ]
                )
                .sort(by='Offence Division',descending=False)
        ).join(
                (
                df_crime
                    .filter(pl.col('Region')==sel_region)
                    .with_columns(pl.col("Offence Division").str.slice(2))
                    .group_by(['Offence Division'])
                    .agg([
                        pl.mean("Incidents Recorded 2025").alias(sel_region + ' Incidents Avg')
                        ,pl.mean("# change").alias(sel_region + ' Incident Avg Change')
                    ]
                    )
                    .with_columns(pl.col(sel_region + ' Incidents Avg').cast(pl.Int64))
                    .with_columns(pl.col(sel_region + ' Incident Avg Change').cast(pl.Int64))
                    .sort(by='Offence Division',descending=False)
            ),
            on='Offence Division',
            how='left'
        )

        df_filtered_crime = df_crime_summary_stg.select([df_crime_summary_stg.columns[0],df_crime_summary_stg.columns[1],
                                                        df_crime_summary_stg.columns[3],df_crime_summary_stg.columns[2],
                                                        df_crime_summary_stg.columns[4]])


    st.dataframe(
        df_filtered_crime,
        width=1000,
        height=300
    )


    ""
    st.write("Source Data: Australian Bureau of Statistics (ABS)")

with tab2:
    st.title("📖 Definitions")
    "Suburbs in each region:"
    st.dataframe(df_map.filter(pl.col("Region")!='Other'),width=1000,height=300)
    "Source Data: 1) https://www.crimestatistics.vic.gov.au/ 2) https://www.abs.gov.au/statistics/people/population/regional-population"
    
with tab3:
    st.title("📋 Release Notes")
    "July 5th 2025 - Completed v1.0 of website. Includes crimes data, population data, area km2 data"

    st.title("🔭 Future Updates")
    "~ July 21st 2025 - Add age, ethnicity, religion data"
    "~ Aug 1st 2025 - Add property price data, rental data"
    "~ Aug 14th 2025 - Add livability data: public transport, distance from commercial areas, parks, schools"
    "Got suggestions for stuff to add to this site? Send them in here: https://forms.gle/ccUuXaaiYmd4bK4X7"