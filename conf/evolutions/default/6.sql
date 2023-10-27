# --- !Ups
UPDATE  tb_machine_times
SET dt_starttime = PRINTF('%02d', (dt_starttime / 1000000000)/ 3600) ||  ":" || PRINTF('%02d',((dt_starttime / 1000000000)/ 60) % 60) ,
dt_endtime = PRINTF('%02d',(dt_endtime / 1000000000)/ 3600 ) ||  ":"|| PRINTF('%02d',((dt_endtime / 1000000000)/ 60) % 60)
WHERE dt_endtime NOT LIKE '%:%'
