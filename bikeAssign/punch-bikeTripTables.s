RUN PGM=MATRIX

  MATI[1]   = SFPT%TOD%.MAT
  PRINTO[1] = bike_model_input\triptable_%TOD%.csv

  PRINT PRINTO=1, LIST=I(0L)
  JLOOP
    PRINT PRINTO=1, LIST="\\",",",ROUND(MI.1.BIKE)(0L)
  ENDJLOOP
ENDRUN

  
