@echo off
setlocal
title Motor Insurance Analytics

echo ========================================
echo       Motor Insurance Analytics
echo ========================================
echo.

powershell.exe -NoLogo -NoProfile -ExecutionPolicy Bypass -Command "$p='%~f0'; $l=Get-Content -LiteralPath $p; $i=[Array]::IndexOf($l,'# POWERSHELL'); if($i -lt 0){exit 1}; $code=$l[($i+1)..($l.Length-1)] -join [Environment]::NewLine; try { & ([ScriptBlock]::Create($code)) } catch { Write-Error $_; exit 1 }"
if errorlevel 1 (
    echo.
    echo Analytics failed. Review the error above.
    pause
    exit /b 1
)

echo.
echo Analytics completed. See the output folder for reports.
pause
exit /b 0

# POWERSHELL
$ErrorActionPreference = 'Stop'

$projectRoot = Split-Path -Parent $p
$searchRoots = @(
    (Join-Path $projectRoot 'data')
    $projectRoot
    (Join-Path $env:USERPROFILE 'Downloads')
)
$requiredDatasets = @(
    'customers.csv'
    'claims.csv'
    'policies.csv'
    'payments.csv'
    'vehicles.csv'
)
$datasetPaths = @{}

foreach ($dataset in $requiredDatasets) {
    $datasetPath = $null
    foreach ($folder in $searchRoots) {
        $candidate = Join-Path $folder $dataset
        if (Test-Path -LiteralPath $candidate -PathType Leaf) {
            $datasetPath = $candidate
            break
        }
    }

    if (-not $datasetPath) {
        throw "Missing required dataset: $dataset. Place all five CSV files in the project folder, its data subfolder, or your Downloads folder."
    }

    $datasetPaths[$dataset] = $datasetPath
}

Write-Host 'Loading motor insurance datasets...'
$customers = @(Import-Csv -LiteralPath $datasetPaths['customers.csv'])
$claims = @(Import-Csv -LiteralPath $datasetPaths['claims.csv'])
$policies = @(Import-Csv -LiteralPath $datasetPaths['policies.csv'])
$payments = @(Import-Csv -LiteralPath $datasetPaths['payments.csv'])
$vehicles = @(Import-Csv -LiteralPath $datasetPaths['vehicles.csv'])

$outputDirectory = Join-Path $projectRoot 'output'
New-Item -ItemType Directory -Path $outputDirectory -Force | Out-Null

$policies |
    Group-Object policy_type, policy_status |
    ForEach-Object {
        $group = $_.Group
        $amounts = $group | Measure-Object -Property premium_amount -Sum -Average
        [pscustomobject]@{
            PolicyType = $group[0].policy_type
            PolicyStatus = $group[0].policy_status
            PolicyCount = $_.Count
            TotalPremium = $amounts.Sum
            AveragePremium = $amounts.Average
        }
    } |
    Export-Csv -LiteralPath (Join-Path $outputDirectory 'policy_summary.csv') -NoTypeInformation -Encoding UTF8

$claims |
    Group-Object claim_type, claim_status |
    ForEach-Object {
        $group = $_.Group
        $amounts = $group | Measure-Object -Property claim_amount -Sum -Average
        [pscustomobject]@{
            ClaimType = $group[0].claim_type
            ClaimStatus = $group[0].claim_status
            ClaimCount = $_.Count
            TotalClaimAmount = $amounts.Sum
            AverageClaimAmount = $amounts.Average
        }
    } |
    Export-Csv -LiteralPath (Join-Path $outputDirectory 'claims_summary.csv') -NoTypeInformation -Encoding UTF8

$payments |
    Group-Object payment_status |
    ForEach-Object {
        $amounts = $_.Group | Measure-Object -Property payment_amount -Sum -Average
        [pscustomobject]@{
            PaymentStatus = $_.Name
            PaymentCount = $_.Count
            TotalPaymentAmount = $amounts.Sum
            AveragePaymentAmount = $amounts.Average
        }
    } |
    Export-Csv -LiteralPath (Join-Path $outputDirectory 'payments_summary.csv') -NoTypeInformation -Encoding UTF8

$customers |
    Group-Object state |
    ForEach-Object {
        [pscustomobject]@{
            State = $_.Name
            CustomerCount = $_.Count
        }
    } |
    Sort-Object CustomerCount -Descending |
    Export-Csv -LiteralPath (Join-Path $outputDirectory 'customer_state_summary.csv') -NoTypeInformation -Encoding UTF8

$vehicles |
    Group-Object vehicle_type, fuel_type |
    ForEach-Object {
        $group = $_.Group
        $values = $group | Measure-Object -Property vehicle_value -Sum -Average
        [pscustomobject]@{
            VehicleType = $group[0].vehicle_type
            FuelType = $group[0].fuel_type
            VehicleCount = $_.Count
            AverageVehicleValue = $values.Average
            TotalVehicleValue = $values.Sum
        }
    } |
    Export-Csv -LiteralPath (Join-Path $outputDirectory 'vehicle_summary.csv') -NoTypeInformation -Encoding UTF8

$totalPremium = ($policies | Measure-Object -Property premium_amount -Sum).Sum
$totalClaims = ($claims | Measure-Object -Property claim_amount -Sum).Sum
$totalPayments = ($payments | Measure-Object -Property payment_amount -Sum).Sum
$overview = @(
    [pscustomobject]@{ Metric = 'Customers'; Value = $customers.Count }
    [pscustomobject]@{ Metric = 'Policies'; Value = $policies.Count }
    [pscustomobject]@{ Metric = 'Claims'; Value = $claims.Count }
    [pscustomobject]@{ Metric = 'Vehicles'; Value = $vehicles.Count }
    [pscustomobject]@{ Metric = 'Payments'; Value = $payments.Count }
    [pscustomobject]@{ Metric = 'Total policy premium'; Value = $totalPremium }
    [pscustomobject]@{ Metric = 'Total claim amount'; Value = $totalClaims }
    [pscustomobject]@{ Metric = 'Total payment amount'; Value = $totalPayments }
)
$overview |
    Export-Csv -LiteralPath (Join-Path $outputDirectory 'overview.csv') -NoTypeInformation -Encoding UTF8

Write-Host "Analytics complete. Reports saved to: $outputDirectory" -ForegroundColor Green
