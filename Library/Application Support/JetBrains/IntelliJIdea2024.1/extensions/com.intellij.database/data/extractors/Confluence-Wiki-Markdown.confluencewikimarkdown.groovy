/*
 * Available context bindings:
 *   COLUMNS     List<DataColumn>
 *   ROWS        Iterable<DataRow>
 *   OUT         { append() }
 *   FORMATTER   { format(row, col); formatValue(Object, col) }
 *   TRANSPOSED  Boolean
 * plus ALL_COLUMNS, TABLE, DIALECT
 *
 * where:
 *   DataRow     { rowNumber(); first(); last(); data(): List<Object>; value(column): Object }
 *   DataColumn  { columnNumber(), name() }
 */

HEADER_SEPARATOR = "||"
SEPARATOR = "|"
QUOTE     = "\""
NEWLINE   = System.getProperty("line.separator")

def printRow = { values, valueToString ->
  values.eachWithIndex { value, idx ->
    def str = valueToString(value)
    OUT.append(idx == 0 ? SEPARATOR : "")
      .append(str)
      .append(idx != values.size() - 1 ? SEPARATOR : SEPARATOR + NEWLINE)
  }
}

if (!TRANSPOSED) {
  OUT.append(HEADER_SEPARATOR)
  COLUMNS.each { col ->
                        OUT.append(col.name())
                        .append(HEADER_SEPARATOR)
               }
               OUT.append(NEWLINE)
  ROWS.each { row -> printRow(COLUMNS, { FORMATTER.format(row, it) }) }
}
else {
  def values = COLUMNS.collect { new ArrayList<String>() }
  ROWS.each { row -> COLUMNS.eachWithIndex { col, i -> values[i].add(FORMATTER.format(row, col)) } }
  values.each { printRow(it, { it }) }
}