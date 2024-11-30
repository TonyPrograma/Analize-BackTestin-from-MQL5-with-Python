import matplotlib.pyplot as plt
import pandas as pd
import numpy as np
import os


def Red_all_csv(file_path:str)-> dict:
    
    """
    Reads all CSV files in the specified folder, cleans them of BOM if necessary, and returns a 
    dictionary with the filename as key and the DataFrame as value.

    Parameters:
    folder (str): The path to the folder containing the CSV files.

    Returns:
    dict: A dictionary with the filename as key and the corresponding DataFrame as value, 
    grouped by days, including portfolio (combination of the csvs). Inlude DD too.
    """
    
    files       = os.listdir(file_path)
    files_csv   = [file for file in files if file.endswith('.csv')]
    dataframes  = {}
    
    for file in files_csv:
        specific_file_path  = os.path.join(file_path, file)
        
        with open(specific_file_path, 'rb') as f: # Read Binary Mode the archive
            content = f.read()

        if content.startswith(b'\xef\xbb\xbf'): # Delate BOM (0xEF 0xBB 0xBF)
            content = content[3:] 

        temp_file = 'temp_cleaned.csv'
        with open(temp_file, 'wb') as f: # Save the archive Binary Temporally 
            f.write(content)

        # Read the Archive clea, delate empty files and final csv
        column_names = ['DATE', 'BALANCE', 'EQUITY', 'DEPOSIT LOAD']
        
        df = pd.read_csv(temp_file, delimiter='\t', encoding='utf-16', header=None, names=column_names, engine='python', on_bad_lines='skip', skiprows=1)
        df_cleaned              = df.dropna(how='all')
        df_cleaned['DATE']      = pd.to_datetime(df_cleaned['DATE'])
        df_cleaned['BALANCE']   = df_cleaned['BALANCE'].astype(float)
        
        for i in range(1, len(df_cleaned)):
            if df_cleaned.loc[i, 'DEPOSIT LOAD'] > 0 or df_cleaned.loc[i, 'EQUITY'] != df_cleaned.loc[i, 'BALANCE']:
                df_cleaned.loc[i, 'BALANCE'] = df_cleaned.loc[i - 1, 'BALANCE']
        
        df_cleaned['PROFIT']    = 0
        df_cleaned['PROFIT']    = df_cleaned['PROFIT'].astype(float)
        df_cleaned.loc[(df_cleaned.index > 0) & (df_cleaned['BALANCE'] != df_cleaned['BALANCE'].shift()), 'PROFIT'] = df_cleaned['BALANCE'] - df_cleaned['BALANCE'].shift()      
        
        df_cleaned['DRAWDOWN']  = 0
        df_cleaned['DRAWDOWN']  = df_cleaned['DRAWDOWN'].astype(float)
        df_cleaned.loc[(df_cleaned.index > 0) & (df_cleaned['EQUITY'] - df_cleaned['BALANCE'] < 0 ), 'DRAWDOWN'] = df_cleaned['BALANCE'] - df_cleaned['EQUITY'] 
        df_cleaned.loc[(df_cleaned.index > 0) & (df_cleaned['PROFIT'] < 0 ), 'DRAWDOWN'] = abs(df_cleaned['PROFIT'])
        
        os.remove(temp_file) #delate the archive temporaly
        
        df_grouped = df_cleaned.groupby(pd.Grouper(key='DATE', freq ='h')).agg({
            'BALANCE'       : 'last', 
            'EQUITY'        : 'max',   
            'DEPOSIT LOAD'  : 'last', 
            'PROFIT'        : 'sum', 
            'DRAWDOWN'      : 'max', 
        }).reset_index()
        
        df_grouped          = df_grouped.dropna(subset=['BALANCE'])
        dataframes[file]    = df_grouped
        
    dataframes_  = []
    for _, df in dataframes.items():
        df['DATE'] = pd.to_datetime(df['DATE'])
        dataframes_.append(df)

    df_combined = pd.concat(dataframes_, axis=0)
    df_combined.set_index('DATE', inplace=True)
    
    df_grouped_ = df_combined.resample('h').agg({
        'BALANCE'       : 'mean', 
        'EQUITY'        : 'mean',   
        'DEPOSIT LOAD'  : 'sum', 
        'PROFIT'        : 'sum', 
        'DRAWDOWN'      : 'sum', 
    }).reset_index()
    
    df_grouped_['DATE'] = pd.to_datetime(df_grouped_['DATE']) 
    for i in range(1, len(df_grouped_)):    
        if df_grouped_.loc[i, 'PROFIT'] == 0:
            df_grouped_.loc[i, 'BALANCE']  = df_grouped_.loc[i - 1, 'BALANCE'] 
        else:   
            df_grouped_.loc[i, 'BALANCE']  = df_grouped_.loc[i - 1, 'BALANCE']  +  df_grouped_.loc[i, 'PROFIT']
            
    df_grouped_ = df_grouped_.dropna(subset=['EQUITY'])
    dataframes['Portafolio']    = df_grouped_
    
    #In all of them EQUITY was removed, in the future, I must normalize it
    
    #remove the EQUITY and agroup by Days.
    for key, df in dataframes.items():
        if 'EQUITY' in df.columns:
            df = df.drop(columns=['EQUITY'], errors='ignore')
            dataframe = df.groupby(pd.Grouper(key='DATE', freq ='D')).agg({
                'BALANCE'       : 'last', 
                'DEPOSIT LOAD'  : 'max', 
                'PROFIT'        : 'sum', 
                'DRAWDOWN'      : 'max', 
            }).reset_index()
            dataframes[key] = dataframe.dropna(subset = ['BALANCE'])
            #print(dataframes[key])
    return(dataframes)



def Portfolio(dataframes: dict) -> dict:
    """
    Calcula métricas de desempeño para cada DataFrame en el diccionario.

    Parámetros:
    -----------
    dataframes : dict
        Diccionario con DataFrames que contienen las columnas:
        'DATE', 'BALANCE', 'DEPOSIT LOAD', 'PROFIT', 'DRAWDOWN'.

    Retorna:
    --------
    dict
        Diccionario con las métricas calculadas para cada DataFrame.
    """
    resultados = {}

    for key, df in dataframes.items():
        # Asegurar que DATE sea datetime y esté ordenado
        df['DATE'] = pd.to_datetime(df['DATE'])
        df = df.sort_values('DATE').reset_index(drop=True)


        # Cálculos básicos
        retorno_total               = (df['BALANCE'].iloc[-1] - df['BALANCE'].iloc[0])
        retornos_diarios            = df['PROFIT'] / df['BALANCE'].shift(1)
        retornos_diarios            = retornos_diarios.dropna()
        retorno_promedio_diario     = df['PROFIT'].mean()
        volatilidad_diaria          = df['PROFIT'].std()
        retorno_mensual_promedio    = (retorno_promedio_diario) * 21


        # Relación días ganadores/perdedores
        dias_ganadores  = (df['PROFIT'] > 0).sum()
        dias_perdedores = (df['PROFIT'] < 0).sum()
        relacion_ganadores_perdedores = dias_ganadores / dias_perdedores



        # Esperanza matemática
        ganancias               = df['PROFIT'][df['PROFIT'] > 0]
        perdidas                = df['PROFIT'][df['PROFIT'] < 0]
        esperanza_matematica    = (ganancias.mean() * len(ganancias) + perdidas.mean() * len(perdidas)) / len(df)


        # Máxima Drawdown (Flotante)
        max_drawdown        = df['DRAWDOWN'].max()
        
        
        #Maxima reduccion del capital 
        df['CUMMAX_BALANCE']    = df['BALANCE'].cummax()
        df['DRAWDOWN_RED']      = df['CUMMAX_BALANCE'] - df['BALANCE']
        max_reduccion_balance   = df['DRAWDOWN_RED'].max()
        
        dd_start_index = 0
        for index, row in df.iterrows():
            if df.loc[index, 'CUMMAX_BALANCE'] == df.loc[df['DRAWDOWN_RED'].idxmax(), 'CUMMAX_BALANCE']: 
                dd_start_index = index
                break
        
        dd_end_index        = df['DRAWDOWN_RED'].idxmax()
        dd_start_date       = df.loc[dd_start_index, 'DATE']    
        dd_end_date         = df.loc[dd_end_index, 'DATE']   
        
        dias_recuperacion   = df.loc[dd_end_index:].loc[df.loc[dd_end_index:, 'BALANCE'] >=  df.loc[dd_start_index, 'CUMMAX_BALANCE']].index.min()

        # Mayor pérdida en un día
        mayor_perdida = df['PROFIT'].min()
        fecha_perdida = df.loc[df['PROFIT'].idxmin(), 'DATE']


        # Mayor ganancia en un día
        mayor_ganancia = df['PROFIT'].max()
        fecha_ganancia = df.loc[df['PROFIT'].idxmax(), 'DATE']


        # Mayor racha positiva
        racha               = (df['PROFIT'] > 0).astype(int)
        rachas_positivas    = racha.groupby((racha != racha.shift()).cumsum()).transform('sum') * racha
        mayor_racha         = rachas_positivas.max()
        if mayor_racha > 0:
            fin_racha           = rachas_positivas.idxmax()
            inicio_racha        = fin_racha - mayor_racha + 1
            inicio_racha_fecha  = df.loc[inicio_racha, 'DATE']
            fin_racha_fecha     = df.loc[fin_racha, 'DATE']
        else:
            inicio_racha_fecha, fin_racha_fecha = None, None

        # Mayor tiempo sin nuevo máximo
        rolling_max         = df['BALANCE'].cummax()
        tiempo_sin_maximos  = (df['BALANCE'] < rolling_max).astype(int)
        max_sin_maximos     = tiempo_sin_maximos.groupby((tiempo_sin_maximos != tiempo_sin_maximos.shift()).cumsum()).transform('sum')
        mayor_tiempo_sin_maximos = max_sin_maximos.max()
        
        if mayor_tiempo_sin_maximos > 0:
            fin_tiempo          = max_sin_maximos.idxmax()
            inicio_tiempo       = fin_tiempo - mayor_tiempo_sin_maximos + 1
            inicio_tiempo_fecha = df.loc[inicio_tiempo, 'DATE']
            fin_tiempo_fecha    = df.loc[fin_tiempo, 'DATE']
        else:
            inicio_tiempo_fecha, fin_tiempo_fecha = None, None

        # Almacenar resultados
        resultados[key] = {
            'Retorno Total'                     : f"{retorno_total:.2f}",
            'Volatilidad Diaria'                : f"{volatilidad_diaria:.2f}",
            'Retorno Promedio Diario'           : f"{retorno_promedio_diario:.2f}",
            'Retorno Mensual Promedio'          : f"{retorno_mensual_promedio:.2f}",
            'Relación Días Ganadores/Perdedores': f"{relacion_ganadores_perdedores:.2f}",
            'Esperanza Matemática'              : f"{esperanza_matematica:.2f}",
            'Take Profit Promedio'              : f"{ganancias.mean():.2f}",
            'Stop Loss Promedio'                : f"{perdidas.mean():.2f}",
            'Máximo drawdown'                   : f"{max_drawdown:.2f}",
            'Máximo Reducción del Balance'      : f"{max_reduccion_balance:.2f}",
            'Fecha de Máxima Reducción'         : {'Inicio': dd_start_date, 'Final': dd_end_date,},
            # 'Días para Recuperar Máxima Reducción' : f"{dias_recuperacion:.2f}",  # Si es relevante en decimales
            'Mayor Pérdida en un Día'           : {'Monto': f"{mayor_perdida:.2f}", 'Fecha': fecha_perdida,},
            'Mayor Ganancia en un Día'          : {'Monto': f"{mayor_ganancia:.2f}", 'Fecha': fecha_ganancia,},
            'Mayor Racha Positiva'              : {'Días': mayor_racha, 'Inicio': inicio_racha_fecha, 'Final': fin_racha_fecha,},
            'Mayor Tiempo sin Nuevos Máximos'   : {'Inicio': inicio_tiempo_fecha, 'Final': fin_tiempo_fecha,},
        }


    return resultados
        