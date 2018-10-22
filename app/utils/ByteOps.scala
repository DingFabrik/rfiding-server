package utils

object ByteOps {
  /** Converts a seq of bytes to a readable string in hex format. */
  implicit class RichByte(val underlying: Seq[Byte]) extends AnyVal {
    def stringForUI(): String = {
      underlying.map("%02X".format(_)).mkString("|")
    }
  }
}
