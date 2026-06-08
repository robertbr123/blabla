import { Config } from '@remotion/cli/config'

Config.setVideoImageFormat('jpeg')
Config.setOverwriteOutput(true)
// Qualidade alta para postar em rede social.
Config.setCrf(18)
