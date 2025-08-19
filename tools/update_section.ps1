param(
  [Parameter(Mandatory=$true)][string]$File,
  [string]$Start,
  [string]$End,
  [string]$After,
  [string]$Before,
  [string]$SnippetPath,
  [string]$SnippetText,
  [int]$Indent = 0
)

if (-not (Test-Path $File)) { Write-Error "Soubor nenalezen: $File"; exit 1 }
if (-not $SnippetText -and $SnippetPath) {
  $enc = New-Object System.Text.UTF8Encoding($false)
  $SnippetText = [IO.File]::ReadAllText((Resolve-Path $SnippetPath), $enc)
}
if (-not $SnippetText) { Write-Error "Dodej -SnippetText nebo -SnippetPath"; exit 1 }

# naÄŤti pĹŻvodnĂ­ text a zdetekuj CRLF
$bytes = [IO.File]::ReadAllBytes($File)
$enc   = New-Object System.Text.UTF8Encoding($false)
$text  = $enc.GetString($bytes)
$usesCRLF = $text -like "*`r`n*"
$NL = "`n"
$norm = $text -replace "`r`n","`n"

# pĹ™iprav snippet (normalizace + odsazenĂ­)
$snip = $SnippetText -replace "`r`n","`n" -replace "`r","`n"
if ($Indent -gt 0) {
  $pad = " " * $Indent
  $snip = ($snip -split "`n" | % { if ($_ -ne "") { $pad + $_ } else { $_ } }) -join "`n"
}

if ($Start -and $End) {
  $pat = "(?s)(" + [regex]::Escape($Start) + ")(.*?)(" + [regex]::Escape($End) + ")"
  if ($norm -notmatch $pat) { Write-Error "Nenalezeny markery Start/End v $File"; exit 2 }
  $norm = [regex]::Replace($norm, $pat, ("`$1`n{0}`n`$3" -f $snip), 1)
}
elseif ($After) {
  # vloĹľ za prvnĂ­ vĂ˝skyt regexu $After (pouĹľijeme zachycenou skupinu $1)
  $pat = "(" + $After + ")"
  $norm = [regex]::Replace($norm, $pat, ("$1`n{0}" -f $snip), 1)
}
elseif ($Before) {
  $pat = "(" + $Before + ")"
  $norm = [regex]::Replace($norm, $pat, ("{0}`n$1" -f $snip), 1)
}
else {
  Write-Error "PouĹľij buÄŹ -Start/-End, nebo -After/-Before"; exit 3
}

# zĂˇloha a zĂˇpis zpÄ›t s pĹŻvodnĂ­mi konci Ĺ™ĂˇdkĹŻ
Copy-Item $File "$File.bak" -Force
$out = $norm
if ($usesCRLF) { $out = $norm -replace "`n","`r`n" }
[IO.File]::WriteAllText($File, $out, $enc)
Write-Host "Upraveno: $File"