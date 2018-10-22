package utils

trait Summarizer {
  /** Provide short form of string if over a certain length */
  def summarize(item: String): String
}
