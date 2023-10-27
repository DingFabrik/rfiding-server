name := "rfiding-server"

organization := "de.dingfabrik.rfiding"

lazy val root = (project in file(".")).enablePlugins(PlayScala, BuildInfoPlugin)

scalaVersion := "2.13.10"

// Needed to resolve doc & javadoc jars for some packages
resolvers += Resolver.sbtPluginRepo("releases")

libraryDependencies ++= Seq(
  guice,
  "org.specs2"             %% "specs2-core"           % "4.20.0" % "test",
  "org.scalatestplus.play" %% "scalatestplus-play"    % "5.1.0" % Test,
  // Slick, Evolutions & SQLite
  "com.typesafe.play"      %% "play-slick"            % "5.1.0",
  "com.typesafe.play"      %% "play-slick-evolutions" % "5.1.0",
  "org.xerial"             %  "sqlite-jdbc"           % "3.41.2.1",
  // Webjars
  "org.webjars"            %% "webjars-play"          % "2.8.18",
  "org.webjars"            %  "bootstrap"             % "5.3.2",
  "org.webjars"            %  "jquery-ui"             % "1.13.2",
  "org.webjars.npm"        %  "feather-icons"         % "4.29.0",
  "org.webjars"            %  "highlightjs"           % "11.5.0",

  "org.ocpsoft.prettytime" % "prettytime"             % "5.0.8",

  // Secure password hashing
  "de.mkammerer"           %  "argon2-jvm"            % "2.11",

  // Slick code gen. Do we really want that?
  //"com.typesafe.slick" %% "slick-codegen" % "3.2.0"

  // Swagger REST API documentation:
  "org.webjars"            %  "swagger-ui"            % "3.19.0",
)

// Adds additional packages into Twirl
//TwirlKeys.templateImports += "de.dingfabrik.rfiding.controllers._"

// Adds additional packages into conf/routes
// play.sbt.routes.RoutesKeys.routesImport += "de.dingfabrik.rfiding.binders._"

version := "0.5.0"

buildInfoKeys := Seq[BuildInfoKey](name, version, scalaVersion, sbtVersion)

buildInfoPackage := "utils"

buildInfoOptions += BuildInfoOption.BuildTime
