{{/* Expand the name of the chart. */}}
{{- define "spidersilk-app.name" -}}
{{- default .Chart.Name .Values.nameOverride | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/* Fully qualified app name. */}}
{{- define "spidersilk-app.fullname" -}}
{{- if .Values.fullnameOverride }}
{{- .Values.fullnameOverride | trunc 63 | trimSuffix "-" }}
{{- else }}
{{- printf "%s" (include "spidersilk-app.name" .) | trunc 63 | trimSuffix "-" }}
{{- end }}
{{- end }}

{{- define "spidersilk-app.labels" -}}
app.kubernetes.io/name: {{ include "spidersilk-app.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
helm.sh/chart: {{ printf "%s-%s" .Chart.Name .Chart.Version | replace "+" "_" }}
{{- end }}

{{- define "spidersilk-app.selectorLabels" -}}
app.kubernetes.io/name: {{ include "spidersilk-app.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
{{- end }}

{{- define "spidersilk-app.serviceAccountName" -}}
{{- if .Values.serviceAccount.create }}
{{- include "spidersilk-app.fullname" . }}
{{- else }}
{{- .Values.serviceAccount.name | default "default" }}
{{- end }}
{{- end }}
