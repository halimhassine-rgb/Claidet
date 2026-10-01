package com.reelicious.mobile.util

import org.json.JSONObject

fun JSONObject.optStringOrNull(key: String): String? =
    if (isNull(key) || !has(key)) null else optString(key).takeIf { it.isNotEmpty() }
