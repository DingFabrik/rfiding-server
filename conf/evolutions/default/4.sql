# --- !Ups

--- We create a intermediate table instead of just using "ALTER TABLE", so that we can influence the order of the columns.
BEGIN TRANSACTION;
CREATE TEMPORARY TABLE "tb_user_backup" ("pk_id" INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,"dt_email" VARCHAR(254) NOT NULL UNIQUE,"dt_hash" VARCHAR(254) NOT NULL);
INSERT INTO "tb_user_backup" ("pk_id", "dt_email", "dt_hash") SELECT "pk_id", "dt_email", "dt_hash" FROM "tb_user";
DROP TABLE "tb_user";
CREATE TABLE "tb_user" ("pk_id" INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,"dt_name" VARCHAR(254) NOT NULL,"dt_email" VARCHAR(254) NOT NULL UNIQUE,"dt_hash" VARCHAR(254) NOT NULL);
INSERT INTO "tb_user" ("pk_id", "dt_name", "dt_email", "dt_hash") SELECT "pk_id", "" AS "dt_name", "dt_email", "dt_hash" FROM "tb_user_backup";
DROP TABLE "tb_user_backup";
COMMIT;

# --- !Downs
BEGIN TRANSACTION;
CREATE TEMPORARY TABLE "tb_user_backup" ("pk_id" INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,"dt_name" VARCHAR(254) NOT NULL,"dt_email" VARCHAR(254) NOT NULL UNIQUE,"dt_hash" VARCHAR(254) NOT NULL);
INSERT INTO "tb_user_backup" ("pk_id", "dt_name", "dt_email", "dt_hash") SELECT "pk_id", "dt_name", "dt_email", "dt_hash" FROM "tb_user";
DROP TABLE "tb_user";
CREATE TABLE "tb_user" ("pk_id" INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,"dt_email" VARCHAR(254) NOT NULL UNIQUE,"dt_hash" VARCHAR(254) NOT NULL);
INSERT INTO "tb_user" ("pk_id", "dt_email", "dt_hash") SELECT "pk_id", "dt_email", "dt_hash" FROM "tb_user_backup";
DROP TABLE "tb_user_backup";
COMMIT;
