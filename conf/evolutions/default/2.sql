# --- !Ups
INSERT INTO "tb_person" VALUES ( 1,NULL,'Anton Albrecht','anton@dingfabrik.de',1);
INSERT INTO "tb_person" VALUES ( 2,NULL,'Papa Schlumpf',NULL,1);
INSERT INTO "tb_person" VALUES ( 3,NULL,'Berta Brecht',NULL,0);

-- Hash maps to password 'abc'
INSERT INTO "tb_user" VALUES (1,'admin@example.com','$argon2i$v=19$m=128000,t=16,p=4$tSf2YXbdzzpkRU3aazmB7w$kaUl3zaatLrbmjgbL3dRb1zXxb+omunoBFaVRxCsA60');

INSERT INTO "tb_machine" VALUES (1,"Kreissäge","11:22:33:44:55:66","Achtung: Gefährliches Ding!",1);

# --- !Downs
DELETE FROM "tb_user";
DELETE FROM "tb_person";
VACUUM;
