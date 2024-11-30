from Portafolio import Portfolio, Red_all_csv

carpeta_csv = 'Historicos'
# Leer los archivos CSV y obtener los DataFrames en un diccionario
dataframes = Red_all_csv(carpeta_csv)
metricas = Portfolio(dataframes)

for nombre_df, resultados in metricas.items():
    print(f"\n=== Resultados para {nombre_df} ===")
    for metrica, valor in resultados.items():
        if isinstance(valor, dict):  # Si el valor es un diccionario (fechas, etc.)
            print(f"{metrica}:")
            for sub_clave, sub_valor in valor.items():
                print(f"  - {sub_clave}: {sub_valor}")
        else:
            print(f"{metrica}: {valor}")
    print("=" * 40)
