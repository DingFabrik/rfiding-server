# --- !Ups
-- TABLE tb_person ---------------------------------------------------------------
create table "tb_person" ("pk_id" INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,"dt_member_id" VARCHAR(254),"dt_name" VARCHAR(254) NOT NULL,"dt_email" VARCHAR(254),"dt_active" INTEGER NOT NULL);
-- TABLE tb_token ----------------------------------------------------------------
create table "tb_token" ("pk_id" INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,"dt_serial" BLOB NOT NULL,"dt_purpose" VARCHAR(254) NOT NULL,"dt_active" INTEGER NOT NULL,"fk_owner_id" INTEGER NOT NULL,constraint "fk_owner" foreign key("fk_owner_id") references "tb_person"("pk_id") on update NO ACTION on delete RESTRICT);
create unique index "index_serial_token" on "tb_token" ("dt_serial");
-- TABLE tb_unknown_token --------------------------------------------------------
create table "tb_unknown_token" ("dt_serial" BLOB NOT NULL,"fk_machine_id" INTEGER NOT NULL,"dt_read_stamp" INTEGER NOT NULL,constraint "fk_machine" foreign key("fk_machine_id") references "tb_machine"("pk_id") on update NO ACTION on delete NO ACTION);
-- TABLE tb_prepared_token -------------------------------------------------------
create table "tb_prepared_token" ("pk_id" INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,"dt_serial" BLOB NOT NULL,"dt_purpose" VARCHAR(254) NOT NULL);
create unique index "index_serial_prepared_token" on "tb_prepared_token" ("dt_serial");
-- TABLE tb_user -----------------------------------------------------------------
create table "tb_user" ("pk_id" INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,"dt_email" VARCHAR(254) NOT NULL UNIQUE,"dt_hash" VARCHAR(254) NOT NULL);
-- TABLE tb_machine --------------------------------------------------------------
create table "tb_machine" ("pk_id" INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,"dt_name" VARCHAR(254) NOT NULL,"dt_mac_address" VARCHAR(254) NOT NULL,"dt_comment" VARCHAR(254),"dt_active" INTEGER NOT NULL);
create unique index "index_machines_mac_address" on "tb_machine" ("dt_mac_address");
-- TABLE tb_machine_config -------------------------------------------------------
create table "tb_machine_config" (
    "fk_machine_id" INTEGER NOT NULL,
    "dt_runtimer" INTEGER,
    "dt_min_power" INTEGER,
    "dt_ctrl_parameter" VARCHAR(254),
    constraint "fk_machine" foreign key("fk_machine_id") references "tb_machine"("pk_id") on update NO ACTION on delete RESTRICT
);
create unique index "index_machines_config" on "tb_machine_config" (
    "fk_machine_id",
    "dt_runtimer",
    "dt_min_power",
    "dt_ctrl_parameter"
);
-- TABLE tb_machine_times --------------------------------------------------------
create table "tb_machine_times" ("pk_id" INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,"fk_machine_id" INTEGER NOT NULL,"dt_weekdays" VARCHAR(254) NOT NULL,"dt_starttime" INTEGER NOT NULL,"dt_endtime" INTEGER NOT NULL);
create unique index "index_machines_times" on "tb_machine_times" ("pk_id");

# --- !Downs
-- TABLE tb_machine_times --------------------------------------------------------
drop table "tb_machine_times";
-- TABLE tb_machine_config -------------------------------------------------------
drop table "tb_machine_config";
-- TABLE tb_machine --------------------------------------------------------------
drop table "tb_machine";
-- TABLE tb_user -----------------------------------------------------------------
drop table "tb_user";
-- TABLE tb_prepared_token -------------------------------------------------------
drop table "tb_prepared_token";
-- TABLE tb_unknown_token --------------------------------------------------------
drop table "tb_unknown_token";
-- TABLE tb_token ----------------------------------------------------------------
drop table "tb_token";
-- TABLE tb_person ---------------------------------------------------------------
drop table "tb_person";
