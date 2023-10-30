# --- !Ups

-- TABLE tb_log_entry --------------------------------------------------------
CREATE TABLE "tb_log_entry" ("fk_machine_id" INTEGER NOT NULL,"fk_token_id" INTEGER NOT NULL, "dt_access_at" INTEGER NOT NULL, CONSTRAINT "fk_machine" FOREIGN KEY("fk_machine_id") REFERENCES "tb_machine"("pk_id") ON UPDATE NO ACTION ON DELETE RESTRICT,CONSTRAINT "fk_token" FOREIGN KEY("fk_token_id") REFERENCES "tb_token"("pk_id") ON UPDATE NO ACTION ON DELETE RESTRICT);

# --- !Downs
DROP TABLE "tb_log_entry";
