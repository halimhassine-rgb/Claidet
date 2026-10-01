package com.reelicious.mobile.ui.theme

import androidx.compose.foundation.isSystemInDarkTheme
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.darkColorScheme
import androidx.compose.material3.lightColorScheme
import androidx.compose.runtime.Composable

private val LightColors = lightColorScheme(
    primary = ReeliciousPrimary,
    primaryContainer = ReeliciousPrimaryContainer,
    secondary = ReeliciousSecondary,
)

private val DarkColors = darkColorScheme(
    primary = ReeliciousPrimary,
    secondary = ReeliciousSecondary,
)

@Composable
fun ReeliciousTheme(content: @Composable () -> Unit) {
    val colors = if (isSystemInDarkTheme()) DarkColors else LightColors
    MaterialTheme(colorScheme = colors, content = content)
}
