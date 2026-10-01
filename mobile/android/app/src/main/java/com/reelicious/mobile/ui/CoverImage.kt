package com.reelicious.mobile.ui

import android.graphics.BitmapFactory
import androidx.compose.foundation.Image
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Surface
import androidx.compose.runtime.Composable
import androidx.compose.runtime.remember
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.asImageBitmap
import androidx.compose.ui.layout.ContentScale
import androidx.compose.ui.unit.Dp
import androidx.compose.ui.unit.dp

@Composable
fun CoverThumbnail(path: String?, size: Dp = 56.dp) {
    val bitmap = remember(path) {
        path?.let { runCatching { BitmapFactory.decodeFile(it) }.getOrNull() }
    }
    Surface(
        modifier = Modifier.size(size).clip(RoundedCornerShape(8.dp)),
        color = MaterialTheme.colorScheme.surfaceVariant,
    ) {
        if (bitmap != null) {
            Image(
                bitmap = bitmap.asImageBitmap(),
                contentDescription = null,
                modifier = Modifier.size(size),
                contentScale = ContentScale.Crop,
            )
        }
    }
}
