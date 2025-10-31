#!/usr/bin/env python3
import requests
import pandas as pd

def get_historical_temperature(station_id, start_time, end_time, client_id, client_secret):
    """
    Henter historiske temperaturdata fra Frost API.
    
    Ifølge Frost API-dokumentasjonen (f.eks. https://frost.met.no/python_example.html)
    er lufttemperaturen tilgjengelig med timelig oppløsning.
    
    Parametre:
      - station_id: Frost-stasjons-ID (f.eks. "SN17820" for E6 Nøstvet)
      - start_time, end_time: ISO 8601-strenger (f.eks. "2025-02-07T00:00:00Z")
      - client_id: Din Frost API-klient-ID.
      - client_secret: Din Frost API-klienthemmelighet (brukes ikke for autentisering)
    """
    endpoint = "https://frost.met.no/observations/v0.jsonld"
    params = {
        "sources": station_id,
        "elements": "air_temperature",
        "referencetime": f"{start_time}/{end_time}",
        "limit": 1000  # Juster om nødvendig
    }
    
    # Autentisering med client_id (passordet er tomt som kreves)
    response = requests.get(endpoint, params=params, auth=(client_id, ""))
    response.raise_for_status()
    data = response.json()

    records = []
    for item in data.get("data", []):
        time_stamp = item.get("referenceTime")
        temperature = None
        if item.get("observations"):
            temperature = item["observations"][0].get("value")
        records.append({"time": time_stamp, "air_temperature": temperature})
    
    df_temp = pd.DataFrame(records)
    if not df_temp.empty:
        # Konverter 'time' til datetime med UTC
        df_temp["time"] = pd.to_datetime(df_temp["time"], utc=True, errors="coerce")
    return df_temp

def merge_energy_and_temperature(energy_file, temp_df, output_file, sep=";", debug=True):
    """
    Leser minuttsbasert energidata og slår sammen med temperaturdata.
    
    Energidata forventes å ha en kolonne 'timestamp_utc'.
    Temperaturdata er timelig (fra Frost API, resamplet til time).
    
    Sammenslåingen gjøres med merge_asof slik at hver energimåling får den 
    siste temperaturverdien før eller lik energitidspunktet.
    Etter sammenslåing sorteres dataene slik at for hver sensor (meter_id)
    er dataene ordnet kronologisk.
    """
    # Last inn energidata (minuttnivå)
    energy_df = pd.read_csv(energy_file, sep=sep, low_memory=False)
    if "timestamp_utc" not in energy_df.columns:
        raise KeyError("Kolonnen 'timestamp_utc' mangler i energidataene.")
    energy_df["timestamp_utc"] = pd.to_datetime(energy_df["timestamp_utc"], utc=True, errors="coerce")
    
    # Sørg for at begge datasett er sortert etter tid
    energy_df.sort_values(by="timestamp_utc", inplace=True)
    temp_df.sort_values(by="time", inplace=True)
    
    # Merge med merge_asof (bruker backward for å hente den siste tilgjengelige temperaturverdien)
    merged_df = pd.merge_asof(
        energy_df,
        temp_df,
        left_on="timestamp_utc",
        right_on="time",
        direction="backward"
    )
    
    # Hvis du ikke ønsker å beholde temperaturens egen tidskolonne 'time', kan du droppe den:
    merged_df.drop(columns=["time"], inplace=True)
    
    # Sørg for at air_temperature er numerisk (konverter evt. tekstverdier til NaN)
    merged_df["air_temperature"] = pd.to_numeric(merged_df["air_temperature"], errors="coerce")
    
    # Sorter slik at for hver sensor (meter_id) er dataene kronologisk ordnet
    merged_df.sort_values(by=["meter_id", "timestamp_utc"], inplace=True)
    
    # Lagre den sammenslåtte datafilen
    merged_df.to_csv(output_file, index=False, sep=sep)
    if debug:
        print("Sammenslåtte data lagret til", output_file)
        print("\nEksempel på sammenslåtte data:")
        print(merged_df.head(10))

def main():
    # --- Temperaturdata-henting med Frost API ---
    # For testing, bruk et mindre tidsintervall (juster etter behov)
    start_time = "2025-02-07T00:00:00Z"
    end_time   = "2025-03-15T00:00:00Z"
    
    station_id = "SN17820"  # Eksempel: E6 Nøstvet
    client_id = "b8ad9a14-3215-41a0-9a1a-7c11cf666b8e"
    client_secret = "ce74e78a-3107-47fe-b10b-b7eb69b0c5cf"  # Ikke brukt for autentisering

    print("Henter temperaturdata fra Frost API ...")
    temp_df = get_historical_temperature(station_id, start_time, end_time, client_id, client_secret)
    
    if temp_df.empty:
        print("Ingen temperaturdata ble hentet!")
        return

    print("Temperaturdata (før resampling):")
    print(temp_df.head())
    
    # Resample til timeoppløsning (beregn gjennomsnitt)
    temp_df.set_index("time", inplace=True)
    hourly_df = temp_df.resample("H").mean().reset_index()
    # Tving konvertering til numerisk (dersom enkelte verdier feiler)
    hourly_df["air_temperature"] = pd.to_numeric(hourly_df["air_temperature"], errors="coerce")
    hourly_df.to_csv("temperature_history.csv", index=False, sep=";")
    print("Temperaturdata eksportert til temperature_history.csv")
    
    # --- Sammenslåing med energidata ---
    energy_file = "processed_minute_data_datek_API.csv"
    output_file = "energy_and_temperature_minute_data.csv"
    
    merge_energy_and_temperature(energy_file, hourly_df, output_file, sep=";", debug=True)

if __name__ == "__main__":
    main()
