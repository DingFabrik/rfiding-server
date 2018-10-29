package utils

import play.api.data.FormError
import play.api.data.format.Formats.parsing
import play.api.data.format.Formatter
import utils.time.Weekday
import controllers.ApiController.formatTokenSeq
import utils.ByteOps.RichByte

package object forms {
  implicit def weekdayFormatter: Formatter[Weekday] = new Formatter[Weekday] {
    override val format: Option[(String, Seq[Any])] = Some(("format.weekday", Seq.empty))
    override def bind(key: String, data: Map[String, String]): Either[Seq[FormError], Weekday] = {
      parsing(incoming => Weekday.week.find(day => day.toString == incoming).get, "error.weekday", Seq.empty)(key, data)
    }
    override def unbind(key: String, value: Weekday): Map[String, String] = {
      Map(key -> value.toString)
    }
  }

  implicit def seqByteFormatter: Formatter[Seq[Byte]] = new Formatter[Seq[Byte]] {
    override val format: Option[(String, Seq[Any])] = Some(("format.seqByte", Seq.empty))
    override def bind(key: String, data: Map[String, String]): Either[Seq[FormError], Seq[Byte]] = {
      parsing(formatTokenSeq, "error.seqByte", Seq.empty)(key, data)
    }
    override def unbind(key: String, value: Seq[Byte]): Map[String, String] = {
      Map(key -> value.asString)
    }
  }
}
