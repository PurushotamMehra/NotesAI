import 'dart:convert';

import 'package:http/http.dart' as http;

import '../config.dart';
import '../models/note.dart';

class ApiService {
  ApiService({http.Client? client}) : _client = client ?? http.Client();

  final http.Client _client;

  Future<Map<String, dynamic>> createNote(String input) async {
    return _postJson('/api/notes/', {'raw_input': input, 'input_type': 'text'});
  }

  Future<List<Note>> searchNotes(String query) async {
    final data = await _postJson('/api/search/', {'query': query});
    final results = data['results'] as List<dynamic>? ?? [];
    return results
        .map((item) => Note.fromJson(item as Map<String, dynamic>))
        .toList();
  }

  Future<Map<String, dynamic>> chat(String query, {int? sessionId}) {
    final body = <String, dynamic>{'query': query};
    if (sessionId != null) {
      body['session_id'] = sessionId;
    }
    return _postJson('/api/chat/', body);
  }

  Future<Note> updateNote(Note note, String rawInput) async {
    final data = await _patchJson('/api/notes/${note.id}/', {
      'raw_input': rawInput,
      'input_type': 'text',
    });
    return Note.fromJson(data);
  }

  Future<Note> reprocessNote(Note note) async {
    final data = await _postJson('/api/notes/${note.id}/reprocess/', {});
    return Note.fromJson(data);
  }

  Future<void> deleteNote(Note note) async {
    final response = await _client.delete(
      Uri.parse('$BASE_URL/api/notes/${note.id}/'),
    );
    if (response.statusCode < 200 || response.statusCode >= 300) {
      _decodeResponse(response);
    }
  }

  Future<List<Note>> fetchNotes() async {
    final response = await _client.get(Uri.parse('$BASE_URL/api/notes/'));
    final data = _decodeResponse(response);
    final results = data['results'] as List<dynamic>? ?? [];
    return results
        .map((item) => Note.fromJson(item as Map<String, dynamic>))
        .toList();
  }

  Future<Map<String, dynamic>> _postJson(
    String path,
    Map<String, dynamic> body,
  ) async {
    final response = await _client.post(
      Uri.parse('$BASE_URL$path'),
      headers: {'Content-Type': 'application/json'},
      body: jsonEncode(body),
    );
    return _decodeResponse(response);
  }

  Future<Map<String, dynamic>> _patchJson(
    String path,
    Map<String, dynamic> body,
  ) async {
    final response = await _client.patch(
      Uri.parse('$BASE_URL$path'),
      headers: {'Content-Type': 'application/json'},
      body: jsonEncode(body),
    );
    return _decodeResponse(response);
  }

  Map<String, dynamic> _decodeResponse(http.Response response) {
    final decoded = response.body.isEmpty
        ? <String, dynamic>{}
        : jsonDecode(response.body);
    if (response.statusCode < 200 || response.statusCode >= 300) {
      final message = decoded is Map<String, dynamic>
          ? decoded['detail']?.toString()
          : null;
      throw ApiException(message ?? 'Request failed');
    }
    return decoded as Map<String, dynamic>;
  }
}

class ApiException implements Exception {
  const ApiException(this.message);

  final String message;

  @override
  String toString() => message;
}
