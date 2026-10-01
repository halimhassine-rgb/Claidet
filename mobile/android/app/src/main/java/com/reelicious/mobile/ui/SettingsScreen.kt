package com.reelicious.mobile.ui

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.ArrowBack
import androidx.compose.material3.Button
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Text
import androidx.compose.material3.TopAppBar
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.input.PasswordVisualTransformation
import androidx.compose.ui.unit.dp

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun SettingsScreen(viewModel: AppViewModel, onBack: () -> Unit) {
    var apiKey by remember { mutableStateOf(viewModel.getApiKey().orEmpty()) }
    var saved by remember { mutableStateOf(false) }

    Scaffold(
        topBar = {
            TopAppBar(
                title = { Text("Réglages") },
                navigationIcon = {
                    IconButton(onClick = onBack) {
                        Icon(Icons.AutoMirrored.Filled.ArrowBack, contentDescription = "Retour")
                    }
                },
            )
        },
    ) { padding ->
        Column(
            modifier = Modifier.fillMaxSize().padding(padding).padding(16.dp),
            verticalArrangement = Arrangement.spacedBy(16.dp),
        ) {
            Text(
                "Clé API Anthropic (Claude), utilisée pour reconstruire les recettes " +
                    "directement depuis ce téléphone — aucun serveur intermédiaire. " +
                    "Stockée chiffrée sur cet appareil uniquement.",
            )
            OutlinedTextField(
                value = apiKey,
                onValueChange = {
                    apiKey = it
                    saved = false
                },
                label = { Text("Clé API Anthropic") },
                singleLine = true,
                visualTransformation = PasswordVisualTransformation(),
                modifier = Modifier.fillMaxWidth(),
            )
            Button(
                onClick = {
                    viewModel.setApiKey(apiKey)
                    saved = true
                },
                enabled = apiKey.isNotBlank(),
                modifier = Modifier.fillMaxWidth(),
            ) {
                Text("Enregistrer")
            }
            if (saved) {
                Text("Clé enregistrée.", color = MaterialTheme.colorScheme.primary)
            }
        }
    }
}
