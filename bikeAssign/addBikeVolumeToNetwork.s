; Take the 2010 Network and add bike_network attributes

RUN PGM=network
 NETI[1] = LOADAM_FINAL.net
 LINKI[2]= bike_model_output\Assign.csv, VAR=A,B,BIKE_AM,BIKE_PM, RENAME=BIKE_AM-BIKE_VOL
 NETO    = LOADAM_FINAL_wBike.net,  EXCLUDE=BIKE_PM
 MERGE RECORD=T
ENDRUN

RUN PGM=network
 NETI[1] = LOADPM_FINAL.net
 LINKI[2]= bike_model_output\Assign.csv, VAR=A,B,BIKE_AM,BIKE_PM, RENAME=BIKE_PM-BIKE_VOL
 NETO    = LOADPM_FINAL_wBike.net, EXCLUDE=BIKE_AM
 MERGE RECORD=T
ENDRUN
