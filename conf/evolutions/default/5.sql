# --- !Ups

BEGIN TRANSACTION;
ALTER TABLE "tb_qualification" ADD "dt_comment" VARCHAR(500);
COMMIT;

# --- !Downs
BEGIN TRANSACTION;
ALTER TABLE "tb_qualification" DROP COLUMN "dt_comment";

COMMIT;
