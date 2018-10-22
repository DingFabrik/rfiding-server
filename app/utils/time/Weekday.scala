package utils.time

import java.time.DayOfWeek

/**
 * Weekday trait.
 *
 * Used to store a set of weekdays in the database.
 */
sealed trait Weekday {
  def toDayOfWeek: DayOfWeek
}
object Weekday {
  object Monday    extends Weekday {
    override def toString: String = "MO"
    def toDayOfWeek: DayOfWeek = DayOfWeek.MONDAY
  }

  object Tuesday   extends Weekday {
    override def toString: String = "TU"
    def toDayOfWeek: DayOfWeek = DayOfWeek.TUESDAY
  }

  object Wednesday extends Weekday {
    override def toString: String = "WE"
    def toDayOfWeek: DayOfWeek = DayOfWeek.WEDNESDAY
  }

  object Thursday  extends Weekday {
    override def toString: String = "TH"
    def toDayOfWeek: DayOfWeek = DayOfWeek.THURSDAY
  }

  object Friday    extends Weekday {
    override def toString: String = "FR"
    def toDayOfWeek: DayOfWeek = DayOfWeek.FRIDAY
  }

  object Saturday  extends Weekday {
    override def toString: String = "SA"
    def toDayOfWeek: DayOfWeek = DayOfWeek.SATURDAY
  }

  object Sunday    extends Weekday {
    override def toString: String = "SU"
    def toDayOfWeek: DayOfWeek = DayOfWeek.SUNDAY
  }


  val week = Seq(Monday, Tuesday, Wednesday, Thursday, Friday, Saturday, Sunday)
}
