[
  split("\n")[]
  | rtrimstr("\r")
  | select(startswith("data: "))
  | ltrimstr("data: ")
  | select(. != "[DONE]")
  | fromjson
]
| if any(.[]; .type == "error" or .type == "response.failed" or .type == "response.incomplete") then
    error("Agent stream contains an error or incomplete response")
  elif (any(.[]; .type == "response.output_text.delta" and (.delta | type == "string" and length > 0)) | not) then
    error("Agent stream contains no text delta")
  elif (any(.[];
    .type == "response.completed"
    and .response.status == "completed"
    and .response.error == null
    and any(.response.output[]?;
      .type == "message" and .role == "assistant"
      and any(.content[]?; .type == "output_text" and (.text | type == "string" and test("\\S")))
    )
  ) | not) then
    error("Agent stream contains no completed assistant text response")
  else
    "Responses contract and streaming checks passed"
  end