class Note {
  const Note({
    required this.id,
    required this.summary,
    required this.cleanedNote,
    required this.rawInput,
    required this.people,
    required this.topics,
    required this.processingStatus,
    required this.embeddingStatus,
    required this.processingError,
    required this.embeddingError,
  });

  final int id;
  final String summary;
  final String cleanedNote;
  final String rawInput;
  final List<String> people;
  final List<String> topics;
  final String processingStatus;
  final String embeddingStatus;
  final String processingError;
  final String embeddingError;

  bool get isAiProcessed => processingStatus == 'completed';
  bool get isSearchReady => embeddingStatus == 'completed';
  bool get needsRetry =>
      processingStatus == 'failed' ||
      processingStatus == 'fallback' ||
      embeddingStatus == 'failed';

  factory Note.fromJson(Map<String, dynamic> json) {
    return Note(
      id: (json['note_id'] ?? json['id']) as int,
      summary: (json['summary'] ?? '') as String,
      cleanedNote: (json['cleaned_note'] ?? '') as String,
      rawInput: (json['raw_input'] ?? json['source_text'] ?? '') as String,
      people: _stringList(json['people']),
      topics: _stringList(json['topics']),
      processingStatus: (json['processing_status'] ?? 'completed') as String,
      embeddingStatus: (json['embedding_status'] ?? 'completed') as String,
      processingError: (json['processing_error'] ?? '') as String,
      embeddingError: (json['embedding_error'] ?? '') as String,
    );
  }

  static List<String> _stringList(dynamic value) {
    if (value is! List) {
      return const [];
    }
    return value.map((item) => item.toString()).toList(growable: false);
  }
}
