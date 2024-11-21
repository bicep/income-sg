# Synthetic High-Resolution Income Data Generation for Singapore

## **Overview**
This project generates ~100,000 synthetic individual-level data points for Singapore, capturing:
- **Geographic realism**: Accurate latitude/longitude coordinates based on high-resolution population density data.
- **Socioeconomic diversity**: Income and housing type distributions aligned with property prices and planning area data.

---

## **Datasets**
### **1. Income Data (`income.csv`)**
Contains income distributions at the planning area level. Each planning area has total households and counts in income brackets.

**Example:**
| Planning Area  | Total   | No Working Person | Below $1,000 | $1,000–$1,999 | $2,000–$2,999 | ... | $20,000 & Over |
|----------------|---------|-------------------|--------------|---------------|---------------|-----|----------------|
| Total          | 1,225.3 | 118.8            | 24.0         | 70.0          | 70.6          | ... | 148.6          |
| Ang Mo Kio     | 62.6    | 8.7              | 2.1          | 5.4           | 4.4           | ... | 6.1            |

---

### **2. Population Density Data (`population_density.csv`)**
High-resolution dataset (~90,000 rows) containing latitude/longitude and associated population density.

**Example:**
| Lat      | Lon      | Population Density |
|----------|----------|--------------------|
| 1.3521   | 103.8198 | 500                |
| 1.2951   | 103.8541 | 200                |

---

### **3. Property Prices Data**
Contains property price information, housing types, and lat/lon values.

**Example:**
| full_address         | median_price_per_sqm | mean_price_per_sqm | housing_type | latitude     | longitude     |
|----------------------|-----------------------|---------------------|--------------|--------------|---------------|
| 1 BEACH RD           | 5190.35              | 5388.66            | public       | 1.2951       | 103.8541      |
| 1 BEDOK STH AVE 1    | 5254.24              | 5331.65            | public       | 1.3209       | 103.9337      |
| 1 DELTA AVE          | 7310.92              | 7280.62            | public       | 1.2921       | 103.8286      |

---

### **GeoJSON Files**
Polygons defining the boundaries of **planning areas** and **subzones** in Singapore.

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
     | latitude        | longitude          | median_price_per_sqm | mean_price_per_sqm | housing_type | Planning Area  | Subzone       |
     |------------|--------------|----------------------|---------------------|--------------|----------------|---------------|
     | 1.295097   | 103.854068   | 5190.35             | 5388.66            | public       | DOWNTOWN CORE  | CITY HALL     |
     | 1.320852   | 103.933721   | 5254.24             | 5331.65            | public       | BEDOK          | BEDOK SOUTH   |
     | 1.327969   | 103.922716   | 4165.41             | 4282.90            | public       | BEDOK          | KEMBANGAN     |


   - For `population_density.csv`:
     | latitude      | longitude      | Population Density | Planning Area  | Subzone       |
     |----------|----------|--------------------|----------------|---------------|
     | 1.3521   | 103.8198 | 500                | Bishan         | Marymount     |

---

### **Step 2: Extract Income Distributions by Planning Area**
1. **Input**:
   - `income.csv` (income bracket counts at the planning area level).
   - Spatially joined property price data from Step 1.

2. **Action**:
   - For each planning area:
     - Normalize income bracket counts to get probability distributions (e.g., percentage of households in each bracket).
     - Example for Ang Mo Kio:
       | Income Bracket     | Count | Percentage |
       |--------------------|-------|------------|
       | Below $1,000       | 2.1   | 3.4%       |
       | $1,000–$1,999      | 5.4   | 8.6%       |
       | ...                | ...   | ...        |

3. **Output**:
   - Income probability distributions for each planning area.

---

### **Step 3: Define Income Strata by Property Prices**
1. **Input**:
   - Property prices and income distributions from Steps 1 and 2.

2. **Action**:
   - For each planning area:
     - Divide property prices into **low**, **medium**, and **high** strata (e.g., bottom 25%, middle 50%, top 25%).
     - Map these strata to corresponding income brackets.
       - Low price → Lower income brackets.
       - Medium price → Middle income brackets.
       - High price → Higher income brackets.

3. **Output**:
   | Planning Area  | Subzone       | Price Stratum  | Income Bracket Distribution |
   |----------------|---------------|----------------|-----------------------------|
   | Bishan         | Marymount     | Medium         | $4,000–$8,000              |

---

### **Step 4: Generate Synthetic Individuals**
1. **Input**:
   - Population density data from Step 1.
   - Income distributions and property price strata from Steps 2 and 3.

2. **Action**:
   - **Proportional Sampling**:
     - Use population density as weights to determine how many synthetic individuals to generate per lat/lon point.
   - **Assign Attributes**:
     - For each individual:
       - **Income**: Sample from the income distribution corresponding to the planning area and price stratum.
       - **Housing Type**: Assign based on the subzone’s housing composition.
   - **Jitter Lat/Lon**:
     - Add small random offsets (e.g., ±0.0002 degrees) to each lat/lon for spatial variability.

3. **Output**:
   | ID   | Lat       | Lon        | Planning Area  | Subzone       | Income | Housing Type     |
   |------|-----------|------------|----------------|---------------|--------|------------------|
   | 1    | 1.352103  | 103.819789 | Bishan         | Marymount     | 6,500  | HDB             |
   | 2    | 1.354219  | 103.820125 | Marina South   | Marina Centre | 15,000 | Private Property |

---

### **Step 5: Validation**
1. **Aggregate Synthetic Data**:
   - Summarize income data by planning area and compare to `income.csv` statistics (mean, median, and bracket distributions).

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
