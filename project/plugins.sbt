addSbtPlugin("org.playframework" % "sbt-plugin" % "3.0.0")

addSbtPlugin("com.eed3si9n" % "sbt-buildinfo" % "0.11.0")

addSbtPlugin("com.github.sbt"    % "sbt-native-packager" % "1.9.16")
addSbtPlugin("org.playframework.twirl" % "sbt-twirl"           % "2.0.1")

ThisBuild / libraryDependencySchemes += "org.scala-lang.modules" %% "scala-xml" % VersionScheme.Always