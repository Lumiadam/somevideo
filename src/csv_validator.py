import pandas as pd
import io

def validate_movie_csv(file_contents):
    """
    Validates CSV file content.
    Expects columns: title, genre, description, release_year, duration
    Returns: (is_valid, list_of_errors, dataframe_or_none)
    """
    errors = []
    try:
        # Load CSV using pandas
        df = pd.read_csv(io.StringIO(file_contents))
    except Exception as e:
        return False, [f"CSV 檔案解析失敗，請確認檔案格式是否正確: {str(e)}"], None
        
    required_cols = {"title", "genre", "description", "release_year", "duration"}
    missing_cols = required_cols - set(df.columns)
    if missing_cols:
        return False, [f"CSV 缺少必要欄位: {', '.join(missing_cols)}"], None
        
    # Check for empty file
    if df.empty:
        return False, ["CSV 檔案中無影片資料"], None
        
    # Let's iterate and validate each row
    for index, row in df.iterrows():
        row_num = index + 2  # Row 1 is header, index 0 is Row 2 in Excel/CSV file
        
        # 1. Check for Nulls/NaNs
        for col in required_cols:
            val = row[col]
            if pd.isna(val) or str(val).strip() == "":
                errors.append(f"第 {row_num} 行: 欄位 '{col}' 數值不能為空。")
        
        # 2. Check release_year range and type
        year_val = row["release_year"]
        if not pd.isna(year_val):
            try:
                # Convert to numeric float/int first, then validate
                year_float = float(year_val)
                if not year_float.is_integer():
                    errors.append(f"第 {row_num} 行: 上映年份 '{year_val}' 必須是整數。")
                else:
                    year_int = int(year_float)
                    if year_int < 1800 or year_int > 2100:
                        errors.append(f"第 {row_num} 行: 上映年份 '{year_int}' 超出範圍 (1800 - 2100)。")
            except (ValueError, TypeError):
                errors.append(f"第 {row_num} 行: 上映年份 '{year_val}' 不是有效的數字。")
                
        # 3. Validate duration string
        duration_val = row["duration"]
        if not pd.isna(duration_val) and len(str(duration_val).strip()) == 0:
            errors.append(f"第 {row_num} 行: 片長欄位內容不能為空。")
            
    if errors:
        return False, errors, None
        
    # All passed validation, return True and the cleaned DataFrame
    # Let's ensure release_year is converted to proper int
    df["release_year"] = df["release_year"].astype(float).astype(int)
    # Strip whitespace from string columns
    for col in ["title", "genre", "description", "duration"]:
        df[col] = df[col].astype(str).str.strip()
        
    return True, [], df
