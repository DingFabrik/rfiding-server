package utils.reader

import scala.util.Random

object ReaderUtils {
  def serialToHexString(serial: Seq[Byte]): String = {
    serial.map("%02X".format(_)).mkString("|")
  }

  private[this] val random = new Random()

  def createDummyData(length: Int): Seq[Byte] = {
    val resultArray: Array[Byte] = new Array(length)
    random.nextBytes(resultArray)
    resultArray
  }
}
