package utils

import java.time.{LocalDateTime, LocalTime, ZoneOffset}

import slick.lifted.Isomorphism
import utils.time.Weekday

/** Tell slick how to map specific types. */
object CustomIsomorphisms {

  /**
   * Isomorphism between Seq[Byte] and Array[Byte].
   *
   * Slick knows how to handle Arrays of Byte, but not Seqs of Byte.
   * This mapping tells slick how to map those these types.
   */
  implicit val seqByteIsomorphism: Isomorphism[Seq[Byte], Array[Byte]] = new Isomorphism(
    map   = seq => seq.toArray,
    comap = arr => arr.toSeq
  )

  /**
   * Isomorphism between LocalTime and its representation as a Long value.
   */
  implicit val localTimeIsomorphism: Isomorphism[LocalTime, Long] = new Isomorphism(
    map   = _.toNanoOfDay,
    comap = LocalTime.ofNanoOfDay
  )

  /**
    * Isomorphism between LocalDateTime and its representation as a Long value.
    */
  implicit val localDateTimeIsomorphism: Isomorphism[LocalDateTime, Long] = new Isomorphism(
    map   = _.toEpochSecond(ZoneOffset.UTC),
    comap = LocalDateTime.ofEpochSecond(_, 0, ZoneOffset.UTC)
  )

  /**
   * Isomorphism between a list of weekdays and its string representation.
   *
   * @note It is assumed that the string from the database is valid!
   *       If it's not, the app may crash or other weird stuff happens!
   */
  implicit val seqWeekdayIsomorphism: Isomorphism[Seq[Weekday], String] = new Isomorphism(
    map   = _.mkString(","),
    comap = _.split(",").map { dayAsString => Weekday.week.find(_.toString == dayAsString.trim.toUpperCase).get }
  )
}
