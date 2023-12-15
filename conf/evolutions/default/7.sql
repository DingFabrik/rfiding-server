# --- !Ups

BEGIN TRANSACTION;
ALTER TABLE "tb_user" ADD "dt_language" VARCHAR(500) NOT NULL DEFAULT('en');
COMMIT;

# --- !Downs
BEGIN TRANSACTION;
ALTER TABLE "tb_user" DROP COLUMN "dt_language";
COMMIT;
