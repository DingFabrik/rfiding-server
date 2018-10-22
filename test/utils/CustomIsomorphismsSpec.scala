package utils

import java.time.LocalTime

import org.specs2.Specification
import org.specs2.specification.Tables
import utils.time.Weekday.Monday
import utils.time.Weekday.Tuesday
import utils.time.Weekday.Wednesday
import utils.time.Weekday.Friday
import utils.time.Weekday.Saturday
import utils.time.Weekday.Sunday
import CustomIsomorphisms.seqWeekdayIsomorphism
import CustomIsomorphisms.localTimeIsomorphism

class CustomIsomorphismsSpec extends Specification with Tables {

  def is = s2"""

 A seqWeekdayIsomorphism can
   convert a string to seq of weekdays                  $seqWeekdayIsomorphismComapTest
   convert a seq of weekdays to a string representation $seqWeekdayIsomorphismMapTest

 A localTimeIsomorphism can
   convert a long value to a LocalTime $localTimeIsomorphismComapTest
   and the other way around            $localTimeIsomorphismMapTest
                                 """

  def seqWeekdayIsomorphismComapTest = {
    "Days as String" | "List of Weekdays"                |>
    "MO,TU,WE"       ! Seq(Monday,Tuesday,Wednesday)     |
    "MO,WE,TU"       ! Seq(Monday,Wednesday,Tuesday)     |
    "MO,SU"          ! Seq(Monday,Sunday)                |
    "MO,Su"          ! Seq(Monday,Sunday)                |
    "MO, FR"         ! Seq(Monday,Friday)                |
    "MO, SA , SU"    ! Seq(Monday,Saturday,Sunday)       |
    { (stringInput, seqOutput) => seqWeekdayIsomorphism.comap.apply(stringInput) must_=== seqOutput }
  }

  def seqWeekdayIsomorphismMapTest = {
    "List of Weekdays"            | "Days as String"   |>
    Seq(Monday,Tuesday,Wednesday) ! "MO,TU,WE"         |
    Seq(Monday,Wednesday,Tuesday) ! "MO,WE,TU"         |
    Seq(Monday,Sunday)            ! "MO,SU"            |
    Seq(Monday,Sunday)            ! "MO,SU"            |
    Seq(Monday,Friday)            ! "MO,FR"            |
    Seq(Monday,Saturday,Sunday)   ! "MO,SA,SU"         |
    { (seqInput, stringOutput) => seqWeekdayIsomorphism.map.apply(seqInput) must_=== stringOutput }
  }

  def localTimeIsomorphismComapTest = {
    "Time as Long"                                                                | "LocalTime"                 |>
    (10L*60L*60L*1e9).toLong ! LocalTime.of(10, 0 , 0)     |
    (23L*60L*60L*1e9 + 59L*60L*1e9 + 55L*1e9).toLong ! LocalTime.of(23, 59 , 55)    |
    { (timeAsLong, localTime) => localTimeIsomorphism.comap.apply(timeAsLong) must_=== localTime }
  }

  def localTimeIsomorphismMapTest = {
    "Time as Long"                                                                | "LocalTime"                 |>
    LocalTime.of(10, 0 , 0) ! (10L*60L*60L*1e9).toLong |
    LocalTime.of(23, 59 , 55) ! (23L*60L*60L*1e9 + 59L*60L*1e9 + 55L*1e9).toLong |
    { (localTime, timeAsLong) => localTimeIsomorphism.map.apply(localTime) must_=== timeAsLong }
  }


}
