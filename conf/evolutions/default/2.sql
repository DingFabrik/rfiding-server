# --- !Ups
-- Username: "admin@example.com", Password: "abc":
INSERT INTO "tb_user" VALUES (1,'admin@example.com','$argon2i$v=19$m=128000,t=16,p=4$tSf2YXbdzzpkRU3aazmB7w$kaUl3zaatLrbmjgbL3dRb1zXxb+omunoBFaVRxCsA60');

# --- !Downs
DELETE FROM "tb_user";
VACUUM;
