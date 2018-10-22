package utils

class DefaultSummarizer extends Summarizer {
  /** Provide short form of string if over a certain length */
  def summarize(item: String): String = {
    item.take(3) + "."
  }
}
