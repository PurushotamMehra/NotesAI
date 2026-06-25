import 'package:flutter/material.dart';

import '../models/note.dart';
import '../services/api_service.dart';
import '../theme/app_design.dart';
import '../widgets/memory_status_chips.dart';
import '../widgets/note_detail_sheet.dart';

class SearchScreen extends StatefulWidget {
  const SearchScreen({super.key, ApiService? apiService})
    : _apiService = apiService;

  final ApiService? _apiService;

  @override
  State<SearchScreen> createState() => _SearchScreenState();
}

class _SearchScreenState extends State<SearchScreen> {
  late final ApiService _apiService = widget._apiService ?? ApiService();
  final _controller = TextEditingController();
  List<Note> _results = const [];
  bool _isSearching = false;
  String? _error;
  String _lastQuery = '';

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  Future<void> _search() async {
    final query = _controller.text.trim();
    if (query.isEmpty || _isSearching) {
      return;
    }
    setState(() {
      _isSearching = true;
      _error = null;
      _lastQuery = query;
    });
    try {
      final results = await _apiService.searchNotes(query);
      if (!mounted) return;
      setState(() => _results = results);
    } catch (error) {
      if (!mounted) return;
      setState(() => _error = error.toString());
    } finally {
      if (mounted) {
        setState(() => _isSearching = false);
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    return MinimalScaffold(
      title: 'SEARCH',
      showBackButton: true,
      bottom: Padding(
        padding: const EdgeInsets.fromLTRB(18, 8, 18, 18),
        child: Row(
          children: [
            Expanded(
              child: MinimalTextField(
                controller: _controller,
                hintText: 'Search memories',
                textInputAction: TextInputAction.search,
                onSubmitted: (_) => _search(),
              ),
            ),
            const SizedBox(width: 10),
            Material(
              color: AppColors.textPrimary,
              shape: const CircleBorder(),
              child: IconButton(
                onPressed: _isSearching ? null : _search,
                tooltip: 'Search',
                color: AppColors.surface,
                disabledColor: AppColors.textSecondary,
                icon: const Icon(Icons.search),
              ),
            ),
          ],
        ),
      ),
      child: _buildBody(),
    );
  }

  Widget _buildBody() {
    if (_isSearching && _results.isEmpty) {
      return const Center(
        child: CircularProgressIndicator(
          strokeWidth: 2,
          color: AppColors.greenAccent,
        ),
      );
    }
    if (_error != null) {
      return Center(
        child: Padding(
          padding: const EdgeInsets.all(AppSpacing.page),
          child: Text(_error!, style: AppTextStyles.muted),
        ),
      );
    }
    if (_results.isEmpty) {
      return Center(
        child: Text(
          _lastQuery.isEmpty ? 'Search your memories' : 'No matching memories.',
          style: AppTextStyles.body,
        ),
      );
    }

    return ListView.separated(
      padding: const EdgeInsets.fromLTRB(
        AppSpacing.page,
        26,
        AppSpacing.page,
        AppSpacing.page,
      ),
      itemCount: _results.length,
      separatorBuilder: (_, __) => const SizedBox(height: 12),
      itemBuilder: (context, index) {
        final note = _results[index];
        return SoftCard(
          onTap: () async {
            final changed = await showNoteDetailSheet(
              context,
              note,
              apiService: _apiService,
            );
            if (changed == true) {
              _search();
            }
          },
          padding: const EdgeInsets.fromLTRB(18, 16, 18, 16),
          child: _SearchResult(note: note),
        );
      },
    );
  }
}

class _SearchResult extends StatelessWidget {
  const _SearchResult({required this.note});

  final Note note;

  @override
  Widget build(BuildContext context) {
    final title = note.summary.isEmpty ? 'Untitled memory' : note.summary;
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          title,
          maxLines: 2,
          overflow: TextOverflow.ellipsis,
          style: AppTextStyles.body.copyWith(fontSize: 18),
        ),
        const SizedBox(height: 8),
        Text(
          note.cleanedNote,
          maxLines: 3,
          overflow: TextOverflow.ellipsis,
          style: AppTextStyles.muted.copyWith(fontSize: 15),
        ),
        if (note.people.isNotEmpty || note.topics.isNotEmpty) ...[
          const SizedBox(height: 10),
          Text(
            [
              ...note.people.map((person) => 'Person: $person'),
              ...note.topics.map((topic) => 'Topic: $topic'),
            ].join('  '),
            maxLines: 2,
            overflow: TextOverflow.ellipsis,
            style: AppTextStyles.sectionLabel,
          ),
        ],
        const SizedBox(height: 14),
        MemoryStatusChips(note: note),
      ],
    );
  }
}
