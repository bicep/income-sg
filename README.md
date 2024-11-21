# Synthetic High-Resolution Income Data Generation for Singapore

## **Overview**
This project generates ~100,000 synthetic individual-level data points for Singapore, capturing:
- **Geographic realism**: Accurate latitude/longitude coordinates based on high-resolution population density data.
- **Socioeconomic diversity**: Income and housing type distributions aligned with property prices and planning area data.

## **Datasets**
### **Input Datasets**
1. **Income Data (`income.csv`)**  
   - Contains income statistics at the planning area level.  
   - Example:
     | Planning Area  | Median Income | Mean Income | StdDev Income |
     |----------------|---------------|-------------|---------------|
     | Marina South   | 8000          | 8500        | 1500          |

2. **Population Density Data (`population_density.csv`)**  
   - High-resolution dataset (~90,000 rows) with latitude/longitude and population density.  
   - Example:
     | Lat      | Lon      | Population Density |
     |----------|----------|--------------------|
     | 1.3521   | 103.8198 | 500                |

3. **Property Prices Data**  
   - **HDB Property Prices (`hdb_property_prices.csv`)** and **Private Property Prices (`private_property_prices.csv`)**:
     - Contain property prices, housing types, and lat/lon values.  
     - Example:
       | Lat      | Lon      | Address              | Avg Price    | Housing Type     |
       |----------|----------|----------------------|--------------|------------------|
       | 1.3521   | 103.8198 | "Blk 123 Bishan St"  | 500,000      | HDB             |
       | 1.3532   | 103.8201 | "Marina Tower 1"     | 2,500,000    | Private Property |

4. **GeoJSON Files**  
   - **Planning Areas GeoJSON** and **Subzones GeoJSON**: Polygons defining planning areas and subzones in Singapore.

---

## **Process**
### **Step 1: Spatially Join Lat/Lon to Planning Areas and Subzones**
1. **Input**:
   - `hdb_property_prices.csv`, `private_property_prices.csv`, and `population_density.csv`.
   - GeoJSON files for planning areas and subzones.

2. **Action**:
   - Perform a spatial join to assign each lat/lon point to a planning area and subzone by checking if it falls within the corresponding polygon.

3. **Output**:
   - For `property_prices.csv`:
     | Lat      | Lon      | Avg Price    | Housing Type     | Planning Area  | Subzone       |
     |----------|----------|--------------|------------------|----------------|---------------|
     | 1.3521   | 103.8198 | 500,000      | HDB             | Bishan         | Marymount     |
     | 1.3532   | 103.8201 | 2,500,000    | Private Property | Marina South   | Marina Centre |

   - For `population_density.csv`:
     | Lat      | Lon      | Population Density | Planning Area  | Subzone       |
     |----------|----------|--------------------|----------------|---------------|
     | 1.3521   | 103.8198 | 500                | Bishan         | Marymount     |
     | 1.3543   | 103.8212 | 800                | Marina South   | Marina Centre |

---

### **Step 2: Define Income Strata by Planning Area**
1. **Input**:
   - `income.csv` and spatially joined `property_prices.csv`.

2. **Action**:
   - For each planning area:
     1. Divide property prices into **low**, **medium**, and **high strata** (relative to the planning area):
        - Low: Bottom 25%.
        - Medium: Middle 50%.
        - High: Top 25%.
     2. Map income ranges from `income.csv` to these strata:
        - Low prices → Lower quartiles of income.
        - Medium prices → Around the median income.
        - High prices → Upper quartiles of income.

3. **Output**:
   | Planning Area  | Subzone       | Price Range  | Income Range       |
   |----------------|---------------|--------------|--------------------|
   | Bishan         | Marymount     | Medium       | $4,000–$8,000      |
   | Marina South   | Marina Centre | High         | $8,000–$20,000     |

---

### **Step 3: Generate Synthetic Individuals**
1. **Input**:
   - Spatially joined `population_density.csv`.
   - Income strata and ranges from Step 2.

2. **Action**:
   - **Proportional Sampling**:
     - Use population density as weights to determine how many synthetic individuals to generate per lat/lon point.
   - **Assign Attributes**:
     - For each individual:
       - **Income**: Sample from the income range based on the planning area and price stratum.
       - **Housing Type**: Assign based on the subzone’s housing composition.
   - **Jitter Lat/Lon**:
     - Add small random offsets (e.g., ±0.0002 degrees) to each lat/lon for spatial variability.

3. **Output**:
   | ID   | Lat       | Lon        | Planning Area  | Subzone       | Income | Housing Type     |
   |------|-----------|------------|----------------|---------------|--------|------------------|
   | 1    | 1.352103  | 103.819789 | Bishan         | Marymount     | 6,500  | HDB             |
   | 2    | 1.354219  | 103.820125 | Marina South   | Marina Centre | 15,000 | Private Property |

---

### **Step 4: Validation**
1. **Aggregate Synthetic Data**:
   - Summarize income data by planning area and compare to `income.csv` statistics (mean, median, stddev).

2. **Visualize**:
   - Compare income distributions using histograms or density plots.
   - Map synthetic individuals to ensure alignment with population density and property price patterns.

---

## **Why This Approach Works**
1. **Geographic Realism**:
   - Leverages high-resolution lat/lon points from `population_density.csv` and accurate planning area/subzone boundaries.

2. **Socioeconomic Fidelity**:
   - Stratifies property prices relative to planning areas, ensuring income diversity reflects local context.

3. **Validation-Ready**:
   - Synthetic data is aligned with ground truth statistics in `income.csv`.

---

## **Tools and Techniques**
- **Spatial Analysis**: GeoPandas (Python), QGIS, or ArcGIS for spatial joins.
- **Data Validation**: Pandas, Matplotlib, or Seaborn for analysis and visualization.

---

## **Next Steps**
- Implement the workflow in Python.
- Validate and iterate based on the synthetic data outputs.

---

Feel free to suggest edits or enhancements!

