package object controllers {

  /** Regex to check a Token UID for validity. */
  val TokenRegexString: String = "([0-9a-fA-F]{8})"

  /** Regex to check a MAC address for validity. */
  val MacAddressRegexString: String = "([0-9a-f]{2}:){5}[0-9a-f]{2}"

  def parameterCheck[P, R](
    isParamValid: P => Boolean
  )(
    param: P
  )(
    onInvalidAction: R
  )(
    onValidAction: R
  ): R = {
    if (isParamValid(param)) {
      onValidAction
    } else {
      onInvalidAction
    }
  }
}
