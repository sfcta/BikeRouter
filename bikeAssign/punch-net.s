*echo N,X,Y > freeflow_nodes.csv

RUN PGM=HWYNET
 filei linki=freeflow.net
 fileo linko=freeflow_tmp.dbf,format=dbf
 printo[2] = freeflow_nodes.csv, APPEND=T
 
 PHASE=NODEMERGE
   PRINT PRINTO=2, FORM=L, LIST=NI.1.N(6), "," NI.1.X(18.5), ",", NI.1.Y(18.5)
 ENDPHASE
ENDRUN

*perl4w32 -S dbf2csv.pl freeflow_tmp.dbf
