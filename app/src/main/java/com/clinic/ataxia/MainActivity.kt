package com.clinic.ataxia

import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.activity.viewModels
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.Button
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Text
import androidx.compose.material3.TopAppBar
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import androidx.lifecycle.ViewModel
import androidx.lifecycle.ViewModelProvider
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import com.clinic.ataxia.domain.model.TraversalMetrics
import com.clinic.ataxia.domain.model.TraversalSession
import com.clinic.ataxia.ui.MainViewModel
import com.clinic.ataxia.ui.theme.AtaxiaMonitorTheme

class MainActivity : ComponentActivity() {

    private val viewModel: MainViewModel by viewModels {
        object : ViewModelProvider.Factory {
            @Suppress("UNCHECKED_CAST")
            override fun <T : ViewModel> create(modelClass: Class<T>): T {
                val app = application as AtaxiaMonitorApp
                return MainViewModel(app.sensorRepository) as T
            }
        }
    }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContent {
            AtaxiaMonitorTheme {
                MainScreen(viewModel = viewModel)
            }
        }
    }
}

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun MainScreen(viewModel: MainViewModel) {
    val uiState by viewModel.uiState.collectAsStateWithLifecycle()

    Scaffold(
        topBar = {
            TopAppBar(title = { Text(text = "Ataxia Monitor") })
        }
    ) { paddingValues ->
        Column(
            modifier = Modifier
                .padding(paddingValues)
                .fillMaxSize()
                .verticalScroll(rememberScrollState())
                .padding(16.dp),
            verticalArrangement = Arrangement.spacedBy(16.dp)
        ) {
            PatientInputSection(
                patientId = uiState.patientId,
                notes = uiState.notes,
                onPatientChange = viewModel::updatePatientId,
                onNotesChange = viewModel::updateNotes
            )

            SessionControls(
                isSessionActive = uiState.isSessionActive,
                onStart = viewModel::startSession,
                onStop = viewModel::stopSession
            )

            LiveMetricsCard(metrics = uiState.liveMetrics)

            SessionHistorySection(sessions = uiState.sessions)
        }
    }
}

@Composable
fun PatientInputSection(
    patientId: String,
    notes: String,
    onPatientChange: (String) -> Unit,
    onNotesChange: (String) -> Unit
) {
    Column(verticalArrangement = Arrangement.spacedBy(8.dp)) {
        Text(
            text = "Participant metadata",
            style = MaterialTheme.typography.titleMedium
        )
        OutlinedTextField(
            value = patientId,
            onValueChange = onPatientChange,
            modifier = Modifier.fillMaxWidth(),
            label = { Text(text = "Patient identifier") },
            singleLine = true
        )
        OutlinedTextField(
            value = notes,
            onValueChange = onNotesChange,
            modifier = Modifier.fillMaxWidth(),
            label = { Text(text = "Clinical notes") },
            minLines = 2
        )
    }
}

@Composable
fun SessionControls(
    isSessionActive: Boolean,
    onStart: () -> Unit,
    onStop: () -> Unit
) {
    Row(
        modifier = Modifier.fillMaxWidth(),
        horizontalArrangement = Arrangement.spacedBy(12.dp),
        verticalAlignment = Alignment.CenterVertically
    ) {
        Button(
            onClick = onStart,
            enabled = !isSessionActive,
            modifier = Modifier.weight(1f)
        ) {
            Text(text = "Start session")
        }
        Button(
            onClick = onStop,
            enabled = isSessionActive,
            modifier = Modifier.weight(1f)
        ) {
            Text(text = "Stop session")
        }
    }
}

@Composable
fun LiveMetricsCard(metrics: TraversalMetrics?) {
    Card(
        modifier = Modifier.fillMaxWidth(),
        colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surfaceVariant)
    ) {
        Column(modifier = Modifier.padding(16.dp)) {
            Text(
                text = "Live metrics",
                style = MaterialTheme.typography.titleMedium,
                fontWeight = FontWeight.Bold
            )
            Spacer(modifier = Modifier.height(12.dp))
            MetricRow(
                label = "Distance traveled",
                value = metrics?.distanceMillimeters?.let { formatNumber(it, suffix = " mm", decimals = 1) } ?: "--"
            )
            MetricRow(
                label = "Radial offset",
                value = metrics?.radialOffsetMillimeters?.let { formatNumber(it, suffix = " mm", decimals = 1) } ?: "--"
            )
            MetricRow(
                label = "Angular velocity",
                value = metrics?.angularVelocity?.let { formatNumber(it, suffix = " rad/s", decimals = 2) } ?: "--"
            )
            MetricRow(
                label = "Tremor magnitude",
                value = metrics?.tremorMagnitude?.let { formatNumber(it, decimals = 2) } ?: "--"
            )
        }
    }
}

@Composable
fun MetricRow(label: String, value: String) {
    Row(
        modifier = Modifier.fillMaxWidth(),
        horizontalArrangement = Arrangement.SpaceBetween
    ) {
        Text(text = label, style = MaterialTheme.typography.bodyMedium)
        Text(text = value, style = MaterialTheme.typography.bodyMedium, fontWeight = FontWeight.SemiBold)
    }
}

@Composable
fun SessionHistorySection(sessions: List<TraversalSession>) {
    Column(verticalArrangement = Arrangement.spacedBy(8.dp)) {
        Text(text = "Session history", style = MaterialTheme.typography.titleMedium)
        if (sessions.isEmpty()) {
            Text(
                text = "No sessions recorded yet",
                modifier = Modifier.fillMaxWidth(),
                textAlign = TextAlign.Center,
                style = MaterialTheme.typography.bodyMedium
            )
        } else {
            sessions.forEach { session ->
                SessionCard(session)
            }
        }
    }
}

@Composable
fun SessionCard(session: TraversalSession) {
    Card(modifier = Modifier.fillMaxWidth()) {
        Column(modifier = Modifier.padding(16.dp)) {
            Text(text = "Session #${session.id}", style = MaterialTheme.typography.titleMedium)
            Spacer(modifier = Modifier.height(4.dp))
            Text(text = "Patient: ${session.patientId}")
            Text(text = "Started: ${formatTimestamp(session.startedAt)}")
            session.endedAt?.let {
                Text(text = "Ended: ${formatTimestamp(it)}")
            }
            session.notes?.let {
                if (it.isNotBlank()) {
                    Spacer(modifier = Modifier.height(4.dp))
                    Text(text = it, style = MaterialTheme.typography.bodySmall)
                }
            }
            Spacer(modifier = Modifier.height(8.dp))
            MetricRow(
                label = "Total distance",
                value = formatNumber(session.metrics.totalDistanceMillimeters, suffix = " mm", decimals = 1)
            )
            MetricRow(
                label = "Avg. offset",
                value = formatNumber(session.metrics.averageOffsetMillimeters, suffix = " mm", decimals = 1)
            )
            MetricRow(
                label = "Peak tremor",
                value = formatNumber(session.metrics.peakTremorMagnitude, decimals = 2)
            )
        }
    }
}

private fun formatTimestamp(value: Long): String =
    android.text.format.DateFormat.format("yyyy-MM-dd HH:mm", value).toString()

private fun formatNumber(value: Float, suffix: String = "", decimals: Int = 2): String {
    val pattern = buildString {
        append("%.")
        append(decimals)
        append("f")
    }
    return String.format(java.util.Locale.getDefault(), pattern, value) + suffix
}
