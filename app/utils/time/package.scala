package utils

import java.time.Clock
import java.time.Instant
import java.time.LocalDateTime
import java.time.ZoneOffset
import java.util.Date

import org.ocpsoft.prettytime.PrettyTime

package object time {

  // Make PrettyTime accept LocalDateTime
  implicit class RichLocalDateTime(val underlying: LocalDateTime) extends AnyVal {
    def pretty(): String = {
      val underlyingDate = Date.from(underlying.toInstant(ZoneOffset.UTC))
      val nowDate = Date.from(Instant.now(Clock.systemUTC()))
      val prettyTime = new PrettyTime(nowDate)
      prettyTime.format(underlyingDate)
    }
  }
}
