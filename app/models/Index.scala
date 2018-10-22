package models

/**
 * Index names for our database.
 *
 * SQLite requires names of indices to be unique across the database.
 * This helper object is meant to provide unique index names.
 */
private[models] object Index {
  val tokenTableIndex = "index_serial_token"
  val preparedTokenTableIndex = "index_serial_prepared_token"
  val machineTableIndex = "index_machines_mac_address"
  val machineTimesTableIndex = "index_machines_times"
  val machineConfigTableIndex = "index_machines_config"
}
