# --- !Ups

-- TABLE tb_qualification --------------------------------------------------------
CREATE TABLE "tb_qualification" ("fk_machine_id" INTEGER NOT NULL,"fk_person_id" INTEGER NOT NULL,CONSTRAINT "fk_machine" FOREIGN KEY("fk_machine_id") REFERENCES "tb_machine"("pk_id") ON UPDATE NO ACTION ON DELETE RESTRICT,CONSTRAINT "fk_person" FOREIGN KEY("fk_person_id") REFERENCES "tb_person"("pk_id") ON UPDATE NO ACTION ON DELETE RESTRICT);
CREATE UNIQUE INDEX "index_qualification" ON "tb_qualification" ("fk_machine_id","fk_person_id");


# --- !Downs
DROP INDEX "index_qualification";
DROP TABLE "tb_qualification";
